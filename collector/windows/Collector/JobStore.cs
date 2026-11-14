using System.Globalization;
using System.Text.Json;
using System.Reflection;
using Microsoft.Data.Sqlite;

namespace Collector;

internal sealed partial class JobStore : IDisposable
{
    private readonly SqliteConnection db;
    private readonly string? snapshotPath;
    private readonly string? snapshotHash;
    public string WorkerId { get; }
    public JobStore(string directory, string? snapshotPath = null, string? snapshotHash = null, bool enableCompanion = false)
    {
        companionEnabled = enableCompanion;
        this.snapshotPath = snapshotPath; this.snapshotHash = snapshotHash;
        Directory.CreateDirectory(directory);
        db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(directory, "jobs.sqlite"), Pooling = false }.ToString());
        db.Open();
        try
        {
            bool hasMetadata = Scalar("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'") is string;
            string? version = hasMetadata ? (string?)Scalar("SELECT value FROM metadata WHERE key='schema_version'") : null;
            if (hasMetadata ? version is not ("1" or "2") : (long)Scalar("SELECT count(*) FROM sqlite_master WHERE type='table'")! != 0)
                throw new RequestError("unsupported_database_schema");
            if (version == "1") MigrateSchema1(directory);
        }
        catch { db.Dispose(); throw; }
        Run("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA busy_timeout=5000; PRAGMA max_page_count=65536;");
        using (var initialization = db.BeginTransaction())
        {
            Run("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, idem TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL,
                    payload TEXT NOT NULL, state TEXT NOT NULL, priority INTEGER NOT NULL,
                    created_at TEXT NOT NULL, expires_at TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0,
                    result TEXT, result_hash TEXT, error TEXT, job_type TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0, lease_hash TEXT, lease_expires_at TEXT);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                    state TEXT NOT NULL, at TEXT NOT NULL, digest TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append_only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append_only'); END;
                CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(state,priority,created_at);
                """, initialization);
            Run("INSERT OR IGNORE INTO metadata VALUES ('schema_version','2'); INSERT OR IGNORE INTO metadata VALUES ('worker_id',$id)", initialization, ("$id", Guid.NewGuid().ToString("N")));
            initialization.Commit();
        }
        if ((string?)Scalar("SELECT value FROM metadata WHERE key='schema_version'") != "2") throw new RequestError("unsupported_database_schema");
        WorkerId = (string)Scalar("SELECT value FROM metadata WHERE key='worker_id'")!;
        // Only replay-safe read-only jobs are accepted. Side-effecting jobs must reconcile instead.
        using var tx = db.BeginTransaction();
        var interrupted = new List<(string Id, string Type)>();
        using (var cmd = Command("SELECT id,job_type FROM jobs WHERE state='running'", tx))
        using (var reader = cmd.ExecuteReader()) while (reader.Read()) interrupted.Add((reader.GetString(0), reader.GetString(1)));
        foreach (var (id, type) in interrupted)
        {
            bool safe = type is "diagnostic.echo" or "research.snapshot";
            Run("UPDATE jobs SET state=$state,error=$error,lease_hash=NULL,lease_expires_at=NULL WHERE id=$id", tx,
                ("$id", id), ("$state", safe ? "queued" : "reconciliation_required"), ("$error", safe ? DBNull.Value : "COMPANION_RESTART_OUTCOME_UNKNOWN"));
            Event(id, safe ? "recovered_replay_safe" : "reconciliation_required", "", tx);
        }
        tx.Commit();
    }
    public object Dispatch(JsonElement request)
    {
        ExpireLeases();
        Protocol.Fields(request, "schema_version", "operation", "job", "job_id", "nonce", "lease_token", "result");
        if (!request.TryGetProperty("schema_version", out var version) || !version.TryGetInt32(out var number) || number != 1)
            throw new RequestError("unsupported_schema");
        var op = Protocol.Text(request, "operation", 64);
        Protocol.Fields(request, op switch
        {
            "health" => ["schema_version", "operation", "nonce"],
            "capabilities" => ["schema_version", "operation"],
            "research.snapshot" => ["schema_version", "operation"],
            "jobs.submit" => ["schema_version", "operation", "job"],
            "jobs.get" or "jobs.cancel" => ["schema_version", "operation", "job_id"],
            "companion.claim" => ["schema_version", "operation"],
            "companion.heartbeat" => ["schema_version", "operation", "job_id", "lease_token"],
            "companion.complete" => ["schema_version", "operation", "job_id", "lease_token", "result"],
            _ => throw new RequestError("unsupported_operation")
        });
        return op switch
        {
            "health" => Health(request),
            "capabilities" => new { schema_version = 1, operations = companionEnabled ? new[] { "health", "capabilities", "jobs.submit", "jobs.get", "jobs.cancel", "research.snapshot", "companion.claim", "companion.heartbeat", "companion.complete" } : ["health", "capabilities", "jobs.submit", "jobs.get", "jobs.cancel", "research.snapshot"],
                job_types = companionEnabled ? new[] { "diagnostic.echo", "research.snapshot", "narration.generate", "editor.operation" } : ["diagnostic.echo", "research.snapshot"], research_snapshot_configured = snapshotPath is not null,
                editor_jobs_enabled = companionEnabled, editor_operations = EditorOperations, editor_export_jobs_enabled = false, narration_jobs_enabled = companionEnabled, narration_backend_ready = false,
                narration_block_reason = companionEnabled ? "remote_narrator_readiness_not_verified" : "user_session_companion_disabled", media_reconciliation_hold = MediaHeld(), publication_paused = true, production_scheduler_enabled = false },
            "research.snapshot" => ResearchSnapshot(),
            "jobs.submit" => Submit(request.GetProperty("job")),
            "jobs.get" => Get(Protocol.Text(request, "job_id", 32)),
            "jobs.cancel" => Cancel(Protocol.Text(request, "job_id", 32)),
            "companion.claim" => Claim(),
            "companion.heartbeat" => Heartbeat(request),
            "companion.complete" => Complete(request),
            _ => throw new RequestError("unsupported_operation")
        };
    }
    private object Health(JsonElement request) => new
    {
        schema_version = 1, product = "The Knowledge Network Collector", version = "0.1.0", worker_id = WorkerId,
        build = Assembly.GetExecutingAssembly().GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? "unrecorded",
        status = "healthy", transport = "windows-local-named-pipe", nonce = Protocol.Text(request, "nonce", 256),
        execution_context = Microsoft.Extensions.Hosting.WindowsServices.WindowsServiceHelpers.IsWindowsService() ? "windows_service" : "interactive_console",
        narration_companion_enabled = companionEnabled, media_reconciliation_hold = MediaHeld(),
        publication_paused = true, production_scheduler_enabled = false
    };
    public object Submit(JsonElement job)
    {
        Protocol.Fields(job, "schema_version", "job_type", "idempotency_key", "inputs", "created_at", "expires_at", "priority");
        if (!job.TryGetProperty("schema_version", out var v) || !v.TryGetInt32(out var schema) || schema != 1) throw new RequestError("unsupported_schema");
        var type = Protocol.Text(job, "job_type", 64);
        if (type is not ("diagnostic.echo" or "research.snapshot") && !(companionEnabled && type is "narration.generate" or "editor.operation")) throw new RequestError("unsupported_job_type");
        var key = Protocol.Text(job, "idempotency_key", 128);
        var inputs = job.GetProperty("inputs");
        if (type == "diagnostic.echo") { Protocol.Fields(inputs, "nonce"); Protocol.Text(inputs, "nonce", 256); }
        else if (type == "narration.generate") ValidateNarration(inputs);
        else if (type == "editor.operation") ValidateEditor(inputs);
        else Protocol.Fields(inputs);
        int priority = 0;
        if (job.TryGetProperty("priority", out var p) && (!p.TryGetInt32(out priority) || priority < 0 || priority > 9)) throw new RequestError("invalid_priority");
        var payload = Protocol.Canonical(job);
        var digest = Protocol.Hash(payload);
        using var tx = db.BeginTransaction();
        using (var existing = Command("SELECT id,payload_hash FROM jobs WHERE idem=$key", tx, ("$key", key)))
        using (var reader = existing.ExecuteReader())
        {
            if (reader.Read())
            {
                var id = reader.GetString(0);
                if (reader.GetString(1) != digest) throw new RequestError("idempotency_conflict");
                reader.Close(); tx.Commit(); return Get(id);
            }
        }
        var now = DateTimeOffset.UtcNow;
        var created = Time(job, "created_at", now);
        var expires = Time(job, "expires_at", now.AddHours(1));
        if (created > now.AddMinutes(5) || expires <= now || expires <= created || expires > now.AddDays(7)) throw new RequestError("expired_or_invalid_job_window");
        if ((long)Scalar("SELECT count(*) FROM jobs", tx)! >= 100000) throw new RequestError("job_capacity_reached");
        var jobId = Guid.NewGuid().ToString("N");
        Run("INSERT INTO jobs (id,idem,payload_hash,payload,state,priority,created_at,expires_at,job_type) VALUES ($id,$key,$hash,$payload,'queued',$priority,$created,$expires,$type)", tx,
            ("$id", jobId), ("$key", key), ("$hash", digest), ("$payload", payload), ("$priority", priority), ("$created", created.ToString("O")), ("$expires", expires.ToString("O")), ("$type", type));
        Event(jobId, "queued", digest, tx);
        tx.Commit();
        return Get(jobId);
    }
    private static DateTimeOffset Time(JsonElement value, string name, DateTimeOffset fallback)
    {
        if (!value.TryGetProperty(name, out _)) return fallback;
        var text = Protocol.Text(value, name, 40);
        if (!(text.EndsWith('Z') || text.EndsWith("+00:00", StringComparison.Ordinal)) ||
            !DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out var result) || result.Offset != TimeSpan.Zero)
            throw new RequestError("invalid_" + name);
        return result;
    }
    public object Get(string id)
    {
        if (id.Length != 32 || !Guid.TryParseExact(id, "N", out _)) throw new RequestError("invalid_job_id");
        using var cmd = Command("SELECT state,payload_hash,result,result_hash,error,attempt,created_at,expires_at,job_type,cancel_requested FROM jobs WHERE id=$id", null, ("$id", id));
        using var reader = cmd.ExecuteReader();
        if (!reader.Read()) throw new RequestError("job_not_found");
        if (!reader.IsDBNull(2) && (reader.IsDBNull(3) || Protocol.Hash(reader.GetString(2)) != reader.GetString(3)))
            throw new RequestError("result_digest_mismatch");
        return new
        {
            job_id = id, job_type = reader.GetString(8), state = reader.GetString(0), payload_sha256 = reader.GetString(1), cancel_requested = reader.GetInt32(9) != 0,
            result = reader.IsDBNull(2) ? (JsonElement?)null : JsonSerializer.Deserialize<JsonElement>(reader.GetString(2)),
            result_sha256 = reader.IsDBNull(3) ? null : reader.GetString(3), error = reader.IsDBNull(4) ? null : reader.GetString(4),
            attempt = reader.GetInt32(5), created_at = reader.GetString(6), expires_at = reader.GetString(7),
            review_only = true, publication_eligible = false
        };
    }
    public object Cancel(string id)
    {
        Get(id);
        using var tx = db.BeginTransaction();
        if (Run("UPDATE jobs SET state='cancelled',cancel_requested=1 WHERE id=$id AND state='queued'", tx, ("$id", id)) > 0) Event(id, "cancelled", "", tx);
        if (Run("UPDATE jobs SET cancel_requested=1 WHERE id=$id AND job_type IN ('narration.generate','editor.operation') AND state='running' AND cancel_requested=0", tx, ("$id", id)) > 0) Event(id, "cancel_requested", "", tx);
        tx.Commit();
        return Get(id);
    }
    public void ExecuteNext()
    {
        ExpireLeases();
        string? id = null, payload = null, expires = null, digest = null;
        using (var cmd = Command("SELECT id,payload,expires_at,payload_hash FROM jobs WHERE state='queued' AND job_type IN ('diagnostic.echo','research.snapshot') ORDER BY priority DESC,created_at,id LIMIT 1"))
        using (var reader = cmd.ExecuteReader()) if (reader.Read()) { id = reader.GetString(0); payload = reader.GetString(1); expires = reader.GetString(2); digest = reader.GetString(3); }
        if (id is null) return;
        using (var tx = db.BeginTransaction())
        {
            if (Protocol.Hash(payload!) != digest)
            {
                Run("UPDATE jobs SET state='blocked',error='payload_digest_mismatch' WHERE id=$id", tx, ("$id", id));
                Event(id, "blocked", "", tx); tx.Commit(); return;
            }
            if (DateTimeOffset.Parse(expires!, CultureInfo.InvariantCulture) <= DateTimeOffset.UtcNow)
            {
                Run("UPDATE jobs SET state='expired',error='expired_before_execution' WHERE id=$id", tx, ("$id", id));
                Event(id, "expired", "", tx); tx.Commit(); return;
            }
            Run("UPDATE jobs SET state='running',attempt=attempt+1 WHERE id=$id", tx, ("$id", id));
            Event(id, "running", "", tx); tx.Commit();
        }
        string result;
        try
        {
            using var parsed = JsonDocument.Parse(payload!);
            result = parsed.RootElement.GetProperty("job_type").GetString() switch
            {
                "diagnostic.echo" => Protocol.Encode(new { nonce = parsed.RootElement.GetProperty("inputs").GetProperty("nonce").GetString(), worker_id = WorkerId }),
                "research.snapshot" => Protocol.Encode(ResearchSnapshot()),
                _ => throw new RequestError("unsupported_job_type")
            };
        }
        catch (Exception error) when (error is RequestError or IOException or UnauthorizedAccessException or JsonException or KeyNotFoundException or InvalidOperationException)
        {
            var code = error is RequestError ? error.Message : "snapshot_unavailable";
            using var failed = db.BeginTransaction();
            Run("UPDATE jobs SET state='blocked',error=$error WHERE id=$id", failed, ("$id", id), ("$error", code));
            Event(id, "blocked", "", failed); failed.Commit(); return;
        }
        var hash = Protocol.Hash(result);
        using (var tx = db.BeginTransaction())
        {
            Run("UPDATE jobs SET state='succeeded',result=$result,result_hash=$hash WHERE id=$id", tx, ("$id", id), ("$result", result), ("$hash", hash));
            Event(id, "succeeded", hash, tx); tx.Commit();
        }
    }
    private object ResearchSnapshot()
    {
        if (snapshotPath is null || snapshotHash is null) throw new RequestError("research_snapshot_not_configured");
        var file = new FileInfo(snapshotPath);
        if (!file.Exists || file.Length > 8 * 1024 * 1024 || (file.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new RequestError("invalid_research_snapshot");
        byte[] bytes;
        using (var stream = new FileStream(snapshotPath, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            if (stream.Length > 8 * 1024 * 1024) throw new RequestError("invalid_research_snapshot");
            bytes = new byte[(int)stream.Length]; stream.ReadExactly(bytes);
        }
        var digest = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(bytes));
        if (!string.Equals(digest, snapshotHash, StringComparison.Ordinal)) throw new RequestError("research_snapshot_digest_mismatch");
        using var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 64 });
        var source = document.RootElement;
        if (source.GetProperty("schema_version").GetInt32() != 1) throw new RequestError("unsupported_snapshot_schema");
        var queues = new Dictionary<string, object>();
        foreach (var name in new[] { "FRESH_UPLOAD", "DAILY_TECH_RECAP", "BLOG_VIDEO", "EVERGREEN_TOP10" })
        {
            var queue = source.GetProperty("queues").GetProperty(name);
            if (queue.ValueKind != JsonValueKind.Object) throw new RequestError("invalid_research_snapshot");
            var ids = queue.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal).ToArray();
            if (ids.Any(id => id.Length > 256 || id.Any(char.IsControl))) throw new RequestError("invalid_snapshot_item_id");
            queues[name] = new { count = ids.Length, item_ids = ids.Take(8).ToArray(), ids_truncated = ids.Length > 8 };
        }
        return new { snapshot_sha256 = digest, source_revision = source.GetProperty("revision").GetInt64(),
            source_publication_paused = source.GetProperty("control").GetProperty("publication_paused").GetBoolean(),
            queues, mode = "immutable_staging_snapshot", production_scheduler_enabled = false, publication_eligible = false };
    }
    private void Event(string id, string state, string digest, SqliteTransaction tx) =>
        Run("INSERT INTO events(job_id,state,at,digest) VALUES($id,$state,$at,$digest)", tx, ("$id", id), ("$state", state), ("$at", DateTimeOffset.UtcNow.ToString("O")), ("$digest", digest));
    private SqliteCommand Command(string sql, SqliteTransaction? tx = null, params (string, object)[] values)
    {
        var cmd = db.CreateCommand(); cmd.CommandText = sql; cmd.Transaction = tx;
        foreach (var (key, value) in values) cmd.Parameters.AddWithValue(key, value);
        return cmd;
    }
    private int Run(string sql, params (string, object)[] values) => Run(sql, null, values);
    private int Run(string sql, SqliteTransaction? tx, params (string, object)[] values) { using var cmd = Command(sql, tx, values); return cmd.ExecuteNonQuery(); }
    private object? Scalar(string sql, SqliteTransaction? tx = null, params (string, object)[] values) { using var cmd = Command(sql, tx, values); return cmd.ExecuteScalar(); }
    public void Dispose() => db.Dispose();
}
