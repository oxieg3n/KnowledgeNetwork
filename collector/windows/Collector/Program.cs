using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Hosting.WindowsServices;

namespace Collector;

internal static class Program
{
    public static async Task<int> Main(string[] args)
    {
        try
        {
            if (args.Length == 0) throw new RequestError("usage_serve_health_capabilities_submit_get_cancel_self-test");
            if (args[0] == "install-service" && args.Length <= 2)
            { Console.WriteLine(Protocol.Encode(new { ok = true, result = await ServiceInstall.Install(args.Length == 2 ? args[1] : null) })); return 0; }
            if (args[0] == "remove-service" && args.Length == 1)
            { Console.WriteLine(Protocol.Encode(new { ok = true, result = await ServiceInstall.Remove() })); return 0; }
            if (args[0] == "self-test")
            {
                try { SelfTest.Run(); return 0; }
                catch (InvalidOperationException error) { Console.WriteLine(Protocol.Encode(new { status = "FAILED", assertion = error.Message })); return 1; }
            }
            if (args[0] == "serve")
            {
                string data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "KnowledgeNetworkCollector");
                SecurityIdentifier? client = null;
                string? snapshot = null, snapshotHash = null;
                bool companion = false;
                for (int i = 1; i < args.Length; i++)
                {
                    if (args[i] == "--enable-companion") { companion = true; continue; }
                    if (i + 1 >= args.Length) throw new RequestError("missing_option_value");
                    string option = args[i], value = args[++i];
                    switch (option)
                    {
                        case "--data": data = Path.GetFullPath(value); break;
                        case "--client-sid": client = new SecurityIdentifier(value); break;
                        case "--research-snapshot": snapshot = Path.GetFullPath(value); break;
                        case "--research-sha256": snapshotHash = value; break;
                        default: throw new RequestError("unknown_option");
                    }
                }
                if ((snapshot is null) != (snapshotHash is null) || (snapshotHash is not null &&
                    (snapshotHash.Length != 64 || !snapshotHash.All(c => char.IsAsciiHexDigit(c) && !char.IsUpper(c)))))
                    throw new RequestError("snapshot_path_and_lowercase_sha256_required");
                if (WindowsServiceHelpers.IsWindowsService() && WindowsIdentity.GetCurrent().IsSystem)
                    throw new RequestError("local_system_service_identity_denied");
                LocalPipe.ProtectDirectory(data);
                var builder = Host.CreateApplicationBuilder();
                builder.Services.AddWindowsService(o => o.ServiceName = "KnowledgeNetworkCollector");
                builder.Services.AddSingleton(new WorkerSettings(data, client, snapshot, snapshotHash, companion));
                builder.Services.AddHostedService<PipeWorker>();
                await builder.Build().RunAsync(); return 0;
            }
            string request = args[0] switch
            {
                "health" when args.Length == 2 => Protocol.Encode(new { schema_version = 1, operation = "health", nonce = args[1] }),
                "capabilities" when args.Length == 1 => Protocol.Encode(new { schema_version = 1, operation = "capabilities" }),
                "research-snapshot" when args.Length == 1 => Protocol.Encode(new { schema_version = 1, operation = "research.snapshot" }),
                "submit" when args.Length == 2 => Protocol.Encode(new { schema_version = 1, operation = "jobs.submit", job = ReadJob(args[1]) }),
                "get" when args.Length == 2 => Protocol.Encode(new { schema_version = 1, operation = "jobs.get", job_id = args[1] }),
                "cancel" when args.Length == 2 => Protocol.Encode(new { schema_version = 1, operation = "jobs.cancel", job_id = args[1] }),
                "companion-claim" when args.Length == 1 => Protocol.Encode(new { schema_version = 1, operation = "companion.claim" }),
                "companion-heartbeat" or "companion-complete" when args.Length == 2 => CompanionRequest(args[0], args[1]),
                _ => throw new RequestError("invalid_command_or_arguments")
            };
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            using var pipe = await LocalPipe.Connect(timeout.Token);
            await Protocol.WriteLine(pipe, request, timeout.Token);
            var response = await Protocol.ReadLine(pipe, timeout.Token);
            Console.WriteLine(response);
            using var result = JsonDocument.Parse(response);
            return result.RootElement.GetProperty("ok").GetBoolean() ? 0 : 1;
        }
        catch (Exception error) when (error is RequestError or JsonException or KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException or IOException or UnauthorizedAccessException or OperationCanceledException or System.ComponentModel.Win32Exception or System.ServiceProcess.TimeoutException or System.Security.SecurityException)
        {
            Console.WriteLine(Protocol.Encode(new { ok = false, error = error is RequestError ? error.Message : error.GetType().Name }));
            return 1;
        }
    }
    private static JsonElement ReadJob(string path)
    {
        if (new FileInfo(path).Length > Protocol.MaxBytes) throw new RequestError("job_file_too_large");
        return JsonSerializer.Deserialize<JsonElement>(File.ReadAllText(path));
    }
    private static string CompanionRequest(string verb, string path)
    {
        var file = new FileInfo(path);
        if (!Path.IsPathFullyQualified(path) || path.StartsWith(@"\\", StringComparison.Ordinal) ||
            new DriveInfo(Path.GetPathRoot(path)!).DriveType == DriveType.Network ||
            file.Length > Protocol.MaxBytes || (file.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new RequestError("private_companion_file_required");
        using var identity = WindowsIdentity.GetCurrent();
        ValidatePrivateCompanionAcl(file.GetAccessControl(), identity.User ?? throw new RequestError("windows_user_required"));
        var request = ReadJob(path);
        Protocol.Fields(request, verb == "companion-heartbeat" ? ["job_id", "lease_token"] : ["job_id", "lease_token", "result"]);
        return verb == "companion-heartbeat"
            ? Protocol.Encode(new { schema_version = 1, operation = "companion.heartbeat", job_id = request.GetProperty("job_id"), lease_token = request.GetProperty("lease_token") })
            : Protocol.Encode(new { schema_version = 1, operation = "companion.complete", job_id = request.GetProperty("job_id"), lease_token = request.GetProperty("lease_token"), result = request.GetProperty("result") });
    }
    internal static void ValidatePrivateCompanionAcl(FileSecurity acl, SecurityIdentifier user)
    {
        var allowed = new[] { user, new SecurityIdentifier(WellKnownSidType.LocalSystemSid, null), new SecurityIdentifier(WellKnownSidType.BuiltinAdministratorsSid, null) };
        if (new RawSecurityDescriptor(acl.GetSecurityDescriptorBinaryForm(), 0).DiscretionaryAcl is null ||
            acl.GetOwner(typeof(SecurityIdentifier)) is not SecurityIdentifier owner || !allowed.Contains(owner))
            throw new RequestError("private_companion_file_required");
        var rules = acl.GetAccessRules(true, true, typeof(SecurityIdentifier)).Cast<FileSystemAccessRule>().ToArray();
        if (!rules.Any(rule => (rule.FileSystemRights & FileSystemRights.ReadData) != 0) ||
            rules.Any(rule => rule.AccessControlType != AccessControlType.Allow || !allowed.Contains(rule.IdentityReference)))
            throw new RequestError("private_companion_file_required");
    }
}

internal sealed record WorkerSettings(string Data, SecurityIdentifier? Client, string? Snapshot, string? SnapshotHash, bool CompanionEnabled);
internal sealed class PipeWorker(WorkerSettings settings) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // SQLite and job transitions have one authoritative writer, including pipe requests.
        using var singleton = new FileStream(Path.Combine(settings.Data, "worker.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        using var store = new JobStore(settings.Data, settings.Snapshot, settings.SnapshotHash, settings.CompanionEnabled);
        while (!stoppingToken.IsCancellationRequested)
        {
            using var pipe = LocalPipe.Create(settings.Client);
            var accept = pipe.WaitForConnectionAsync(stoppingToken);
            while (!accept.IsCompleted)
            {
                await Task.WhenAny(accept, Task.Delay(100, stoppingToken));
                if (stoppingToken.IsCancellationRequested) return;
                store.ExecuteNext();
            }
            await accept;
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(5));
            try
            {
                var raw = await Protocol.ReadLine(pipe, timeout.Token);
                using var request = JsonDocument.Parse(raw, new JsonDocumentOptions { MaxDepth = 16 });
                if (request.RootElement.TryGetProperty("operation", out var operation) && operation.GetString() == "jobs.submit" &&
                    new DriveInfo(Path.GetPathRoot(settings.Data)!).AvailableFreeSpace < 256L * 1024 * 1024)
                    throw new RequestError("disk_reserve_reached");
                var result = store.Dispatch(request.RootElement);
                await Protocol.WriteLine(pipe, Protocol.Encode(new { ok = true, result }), timeout.Token);
            }
            catch (Exception error) when (error is RequestError or JsonException or KeyNotFoundException or InvalidOperationException or FormatException or ArgumentException or IOException or OperationCanceledException)
            {
                if (pipe.IsConnected && !timeout.IsCancellationRequested)
                    try { await Protocol.WriteLine(pipe, Protocol.Encode(new { ok = false, error = error is RequestError ? error.Message : "invalid_request" }), timeout.Token); }
                    catch (IOException) { }
            }
            if (!stoppingToken.IsCancellationRequested) store.ExecuteNext();
        }
    }
}
