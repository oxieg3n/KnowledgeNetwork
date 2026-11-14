using System.ComponentModel;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace Collector;

internal static class LocalPipe
{
    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes { public int Length; public IntPtr Descriptor; public int Inherit; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafePipeHandle CreateNamedPipe(string name, uint openMode, uint pipeMode, uint instances,
        uint outBuffer, uint inBuffer, uint timeout, ref SecurityAttributes security);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafePipeHandle CreateFile(string name, uint access, uint share, IntPtr security,
        uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetNamedPipeServerProcessId(SafePipeHandle pipe, out uint processId);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern SafeProcessHandle OpenProcess(uint access, bool inherit, uint processId);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool QueryFullProcessImageName(SafeProcessHandle process, uint flags, StringBuilder name, ref int size);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(SafeProcessHandle process, uint access, out SafeAccessTokenHandle token);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetTokenInformation(SafeAccessTokenHandle token, int kind, IntPtr buffer, int size, out int required);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr OpenSCManager(string? machine, string? database, uint access);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr OpenService(IntPtr manager, string name, uint access);
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool QueryServiceStatusEx(IntPtr service, int level, out ServiceStatusProcess status, int size, out int needed);
    [DllImport("advapi32.dll")]
    private static extern bool CloseServiceHandle(IntPtr handle);
    [StructLayout(LayoutKind.Sequential)]
    private struct ServiceStatusProcess
    {
        public uint Type, State, Controls, ExitCode, SpecificExitCode, Checkpoint, WaitHint, ProcessId, Flags;
    }

    private static bool RegisteredServiceProcess(uint processId)
    {
        var manager = OpenSCManager(null, null, 1);
        if (manager == IntPtr.Zero) return false;
        try
        {
            var service = OpenService(manager, "KnowledgeNetworkCollector", 4);
            if (service == IntPtr.Zero) return false;
            try { return QueryServiceStatusEx(service, 0, out var status, Marshal.SizeOf<ServiceStatusProcess>(), out _) && status.State == 4 && status.ProcessId == processId; }
            finally { CloseServiceHandle(service); }
        }
        finally { CloseServiceHandle(manager); }
    }
    private static void AuthenticateServer(SafePipeHandle pipe)
    {
        if (!GetNamedPipeServerProcessId(pipe, out var processId)) throw new RequestError("untrusted_pipe_server");
        using var process = OpenProcess(0x1000, false, processId);
        var image = new StringBuilder(32768); int length = image.Capacity;
        if (process.IsInvalid || !QueryFullProcessImageName(process, 0, image, ref length) ||
            !string.Equals(image.ToString(), Environment.ProcessPath, StringComparison.OrdinalIgnoreCase))
            throw new RequestError("untrusted_pipe_server");
        if (RegisteredServiceProcess(processId)) return;
        if (!OpenProcessToken(process, 8, out var token)) throw new RequestError("untrusted_pipe_server");
        using (token)
        {
            GetTokenInformation(token, 1, IntPtr.Zero, 0, out int required);
            if (required <= 0 || required > 65536) throw new RequestError("untrusted_pipe_server");
            var buffer = Marshal.AllocHGlobal(required);
            try
            {
                if (!GetTokenInformation(token, 1, buffer, required, out _)) throw new RequestError("untrusted_pipe_server");
                var server = new SecurityIdentifier(Marshal.ReadIntPtr(buffer));
                using var identity = WindowsIdentity.GetCurrent();
                if (identity.User is not { } current || !server.Equals(current)) throw new RequestError("untrusted_pipe_server");
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }
    }

    public static async Task<NamedPipeClientStream> Connect(CancellationToken token)
    {
        while (true)
        {
            token.ThrowIfCancellationRequested();
            // GENERIC_WRITE includes create-instance; request only the rights granted to the owner client.
            var handle = CreateFile(@"\\.\pipe\" + Protocol.PipeName, 0x12019b, 0, IntPtr.Zero, 3, 0x40110000, IntPtr.Zero);
            if (!handle.IsInvalid)
            {
                try { AuthenticateServer(handle); return new NamedPipeClientStream(PipeDirection.InOut, true, true, handle); }
                catch { handle.Dispose(); throw; }
            }
            var error = Marshal.GetLastWin32Error(); handle.Dispose();
            if (error is not (2 or 231)) throw new Win32Exception(error);
            await Task.Delay(50, token);
        }
    }

    public static NamedPipeServerStream Create(SecurityIdentifier? client)
    {
        using var identity = WindowsIdentity.GetCurrent();
        var owner = identity.User ?? throw new InvalidOperationException("missing_windows_identity");
        // Explicit client rights exclude FILE_CREATE_PIPE_INSTANCE (included in generic write).
        var sddl = $"D:P(A;;GA;;;{owner.Value})" + (client is null || client == owner ? "" : $"(A;;0x12019b;;;{client.Value})");
        var descriptor = new RawSecurityDescriptor(sddl);
        byte[] bytes = new byte[descriptor.BinaryLength]; descriptor.GetBinaryForm(bytes, 0);
        var memory = Marshal.AllocHGlobal(bytes.Length);
        try
        {
            Marshal.Copy(bytes, 0, memory, bytes.Length);
            var security = new SecurityAttributes { Length = Marshal.SizeOf<SecurityAttributes>(), Descriptor = memory };
            // FILE_FLAG_FIRST_PIPE_INSTANCE, OVERLAPPED; PIPE_REJECT_REMOTE_CLIENTS enforced by Windows.
            var handle = CreateNamedPipe(@"\\.\pipe\" + Protocol.PipeName, 0x00000003 | 0x40000000 | 0x00080000,
                0x00000008, 1, Protocol.MaxBytes, Protocol.MaxBytes, 0, ref security);
            if (handle.IsInvalid) { var error = Marshal.GetLastWin32Error(); handle.Dispose(); throw new Win32Exception(error); }
            return new NamedPipeServerStream(PipeDirection.InOut, true, false, handle);
        }
        finally { Marshal.FreeHGlobal(memory); }
    }
    public static void ProtectDirectory(string path)
    {
        var directory = new DirectoryInfo(Path.GetFullPath(path));
        bool existed = directory.Exists;
        directory.Create();
        if ((directory.Attributes & FileAttributes.ReparsePoint) != 0) throw new RequestError("data_reparse_point_denied");
        using var identity = WindowsIdentity.GetCurrent();
        var owner = identity.User ?? throw new InvalidOperationException("missing_windows_identity");
        var allowed = new[] { owner, new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null), new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null) }.Distinct().ToArray();
        if (existed)
        {
            var existing = directory.GetAccessControl();
            var rules = existing.GetAccessRules(true, true, typeof(SecurityIdentifier)).Cast<FileSystemAccessRule>().ToArray();
            if (!existing.AreAccessRulesProtected || rules.Any(rule => rule.AccessControlType != AccessControlType.Allow || !allowed.Contains(rule.IdentityReference)) ||
                !rules.Any(rule => rule.IdentityReference.Equals(owner) && (rule.FileSystemRights & FileSystemRights.FullControl) == FileSystemRights.FullControl))
                throw new RequestError("data_directory_acl_not_private");
            return;
        }
        var acl = new DirectorySecurity(); acl.SetAccessRuleProtection(true, false);
        foreach (var sid in allowed)
            acl.AddAccessRule(new FileSystemAccessRule(sid, FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        directory.SetAccessControl(acl);
    }
}
