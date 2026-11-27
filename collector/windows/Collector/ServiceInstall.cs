using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.ServiceProcess;
using System.Text.Json;
using Microsoft.Win32;

namespace Collector;

internal static class ServiceInstall
{
    private const string Name = "KnowledgeNetworkCollector";
    private const string Product = "The Knowledge Network Collector";
    private static readonly string DirectoryPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Product);
    private static readonly string Binary = Path.Combine(DirectoryPath, "kn-collector.exe");
    private static readonly string Data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), Name);
    [StructLayout(LayoutKind.Sequential)]
    private struct Status { public uint Type, State, Controls, Exit, SpecificExit, Checkpoint, Hint, Pid, Flags; }
    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool QueryServiceStatusEx(SafeHandle service, int level, out Status status, int size, out int needed);

    private static SecurityIdentifier CheckAdministrator()
    {
        if (!string.Equals(Environment.ProcessPath, Binary, StringComparison.OrdinalIgnoreCase)) throw new RequestError("canonical_installed_binary_required");
        using var identity = WindowsIdentity.GetCurrent();
        if (!new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator)) throw new RequestError("administrator_required");
        if ((File.GetAttributes(DirectoryPath) & FileAttributes.ReparsePoint) != 0) throw new RequestError("install_reparse_point_denied");
        return identity.User ?? throw new RequestError("windows_user_required");
    }
    private static bool ExistingService()
    {
        using var key = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services\" + Name);
        if (key is null) return false;
        if (key.GetValue("ImagePath") is not string command || !command.StartsWith('"' + Binary + "\" serve ", StringComparison.OrdinalIgnoreCase))
            throw new RequestError("existing_service_path_mismatch");
        return true;
    }
    internal static JsonDocument ReadPackageManifest(string path) =>
        JsonDocument.Parse(File.ReadAllText(path), new JsonDocumentOptions { MaxDepth = 8 });
    private static void VerifyPackage()
    {
        string manifest = Path.Combine(DirectoryPath, "files.sha256.json");
        if (new FileInfo(manifest).Length > 2 * 1024 * 1024 || (File.GetAttributes(manifest) & FileAttributes.ReparsePoint) != 0)
            throw new RequestError("invalid_package_manifest");
        using var document = ReadPackageManifest(manifest);
        if (document.RootElement.ValueKind != JsonValueKind.Array || document.RootElement.GetArrayLength() > 4096) throw new RequestError("invalid_package_manifest");
        var expected = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var entry in document.RootElement.EnumerateArray())
        {
            Protocol.Fields(entry, "path", "sha256");
            var relative = Protocol.Text(entry, "path", 512);
            var path = Path.GetFullPath(Path.Combine(DirectoryPath, relative));
            var digest = Protocol.Text(entry, "sha256", 64);
            if (!path.StartsWith(DirectoryPath + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) || !expected.Add(path) ||
                digest.Length != 64 || digest.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c))) throw new RequestError("invalid_package_manifest");
            var file = new FileInfo(path);
            if (!file.Exists || file.Length > 512L * 1024 * 1024 || (file.Attributes & FileAttributes.ReparsePoint) != 0) throw new RequestError("invalid_package_file");
            for (string? parent = Path.GetDirectoryName(path); !string.Equals(parent, DirectoryPath, StringComparison.OrdinalIgnoreCase); parent = Path.GetDirectoryName(parent!))
                if (parent is null || (File.GetAttributes(parent) & FileAttributes.ReparsePoint) != 0) throw new RequestError("invalid_package_file");
            using var stream = file.OpenRead();
            if (Convert.ToHexStringLower(SHA256.HashData(stream)) != digest) throw new RequestError("package_integrity_mismatch");
        }
        if (!expected.Contains(Binary)) throw new RequestError("package_binary_missing");
        var directories = new Stack<string>(); directories.Push(DirectoryPath); int entries = 0;
        while (directories.TryPop(out var directory)) foreach (var path in System.IO.Directory.EnumerateFileSystemEntries(directory))
        {
            if (++entries > 8192 || (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new RequestError("invalid_package_file");
            if (System.IO.Directory.Exists(path)) { directories.Push(path); continue; }
            bool uninstaller = directory == DirectoryPath && System.Text.RegularExpressions.Regex.IsMatch(Path.GetFileName(path), @"^unins[0-9]{3}\.(exe|dat|msg)$", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
            if (path != manifest && !uninstaller && !expected.Contains(path)) throw new RequestError("unmanifested_package_file");
        }
    }
    private static async Task Sc(params string[] arguments)
    {
        var start = new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "sc.exe"))
        { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        using var process = Process.Start(start) ?? throw new RequestError("service_control_start_failed");
        var output = process.StandardOutput.ReadToEndAsync(); var errors = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { process.Kill(); throw new RequestError("service_control_timeout"); }
        await output; await errors;
        if (process.ExitCode != 0) throw new RequestError("service_" + arguments[0] + "_failed_" + process.ExitCode);
    }
    private static void Stop()
    {
        using var service = new ServiceController(Name);
        if (service.Status == ServiceControllerStatus.Stopped) return;
        if (service.Status != ServiceControllerStatus.StopPending) service.Stop();
        service.WaitForStatus(ServiceControllerStatus.Stopped, TimeSpan.FromSeconds(20));
    }
    private static uint ProcessId()
    {
        using var service = new ServiceController(Name);
        return QueryServiceStatusEx(service.ServiceHandle, 0, out var status, Marshal.SizeOf<Status>(), out _) && status.State == 4 ? status.Pid : 0;
    }
    private static async Task<object> VerifyHealth(string command, bool companion)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        uint stablePid = 0; string? stableWorker = null; int stable = 0;
        while (!deadline.IsCancellationRequested)
        {
            try
            {
                uint before = ProcessId();
                using var probe = CancellationTokenSource.CreateLinkedTokenSource(deadline.Token); probe.CancelAfter(TimeSpan.FromSeconds(10));
                using var pipe = await LocalPipe.Connect(probe.Token);
                string nonce = Guid.NewGuid().ToString("N");
                await Protocol.WriteLine(pipe, Protocol.Encode(new { schema_version = 1, operation = "health", nonce }), probe.Token);
                using var reply = JsonDocument.Parse(await Protocol.ReadLine(pipe, probe.Token));
                var root = reply.RootElement; var health = root.GetProperty("result");
                uint after = ProcessId();
                using var key = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services\" + Name);
                var worker = Protocol.Text(health, "worker_id", 32);
                bool valid = !deadline.IsCancellationRequested && before > 0 && before == after && root.GetProperty("ok").GetBoolean() &&
                    health.GetProperty("schema_version").GetInt32() == 1 && health.GetProperty("nonce").GetString() == nonce &&
                    health.GetProperty("product").GetString() == Product && health.GetProperty("status").GetString() == "healthy" &&
                    health.GetProperty("execution_context").GetString() == "windows_service" && health.GetProperty("publication_paused").GetBoolean() &&
                    !health.GetProperty("production_scheduler_enabled").GetBoolean() && worker.Length == 32 && worker.All(char.IsAsciiHexDigit) &&
                    health.GetProperty("narration_companion_enabled").GetBoolean() == companion &&
                    string.Equals(key?.GetValue("ObjectName") as string, @"NT AUTHORITY\LocalService", StringComparison.OrdinalIgnoreCase) &&
                    string.Equals(key?.GetValue("ImagePath") as string, command, StringComparison.Ordinal);
                stable = valid ? (after == stablePid && worker == stableWorker ? stable + 1 : 1) : 0;
                stablePid = after; stableWorker = worker;
                if (stable >= 2) return new { status = "PASS", service = Name, process_id = after, worker_id = worker, companion_enabled = companion, publication_paused = true };
            }
            catch (Exception error) when (error is RequestError or IOException or OperationCanceledException or JsonException or InvalidOperationException or KeyNotFoundException or System.ComponentModel.Win32Exception) { stable = 0; }
            try { await Task.Delay(300, deadline.Token); } catch (OperationCanceledException) { break; }
        }
        throw new RequestError("service_authenticated_health_failed_data_retained");
    }
    public static async Task<object> Install(string? ownerSid, bool? companionOverride = null)
    {
        var current = CheckAdministrator();
        var owner = ownerSid is null ? current : new SecurityIdentifier(ownerSid);
        if (owner.AccountDomainSid is null || !owner.Equals(current)) throw new RequestError("install_as_configured_owner_required");
        VerifyPackage(); bool existing = ExistingService();
        bool companion = false;
        if (existing)
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services\" + Name);
            companion = System.Text.RegularExpressions.Regex.IsMatch(key?.GetValue("ImagePath") as string ?? "", @"(?:^|\s)--enable-companion(?:\s|$)");
        }
        companion = companionOverride ?? companion;
        if (existing) Stop();
        System.IO.Directory.CreateDirectory(Data);
        if ((File.GetAttributes(Data) & FileAttributes.ReparsePoint) != 0) throw new RequestError("data_reparse_point_denied");
        var acl = new DirectorySecurity(); acl.SetAccessRuleProtection(true, false);
        foreach (string sid in new[] { "S-1-5-19", "S-1-5-18", "S-1-5-32-544" })
            acl.AddAccessRule(new FileSystemAccessRule(new SecurityIdentifier(sid), FileSystemRights.FullControl, InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit, PropagationFlags.None, AccessControlType.Allow));
        new DirectoryInfo(Data).SetAccessControl(acl);
        string command = '"' + Binary + "\" serve --data \"" + Data + "\" --client-sid " + owner.Value;
        if (companion) command += " --enable-companion";
        string snapshot = Path.Combine(Data, "research-staging.json");
        if (File.Exists(snapshot))
        {
            var file = new FileInfo(snapshot);
            if (file.Length > 8 * 1024 * 1024 || (file.Attributes & FileAttributes.ReparsePoint) != 0) throw new RequestError("invalid_research_snapshot");
            using var stream = file.OpenRead(); command += " --research-snapshot \"" + snapshot + "\" --research-sha256 " + Convert.ToHexStringLower(SHA256.HashData(stream));
        }
        await Sc(existing ? "config" : "create", Name, "binPath=", command, "obj=", @"NT AUTHORITY\LocalService", "start=", "auto", "DisplayName=", Product);
        await Sc("description", Name, "Local-only bounded review worker; publication remains paused.");
        await Sc("failure", Name, "reset=", "86400", "actions=", "restart/5000/restart/15000/none/0");
        using (var service = new ServiceController(Name)) { service.Start(); service.WaitForStatus(ServiceControllerStatus.Running, TimeSpan.FromSeconds(20)); }
        return await VerifyHealth(command, companion);
    }
    public static async Task<object> Remove()
    {
        CheckAdministrator();
        if (ExistingService()) { Stop(); await Sc("delete", Name); }
        return new { status = "PASS", service_removed = true, private_data_retained = true, binaries_retained = true };
    }
}
