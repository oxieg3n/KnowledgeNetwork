using System.ComponentModel;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;

namespace Collector;

internal static class LocalPipe
{
    [StructLayout(LayoutKind.Sequential)]
    private struct SecurityAttributes { public int Length; public IntPtr Descriptor; public int Inherit; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern SafePipeHandle CreateNamedPipe(string name, uint openMode, uint pipeMode, uint instances,
        uint outBuffer, uint inBuffer, uint timeout, ref SecurityAttributes security);

    public static NamedPipeServerStream Create(SecurityIdentifier? client)
    {
        var owner = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("missing_windows_identity");
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
        var owner = WindowsIdentity.GetCurrent().User ?? throw new InvalidOperationException("missing_windows_identity");
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
