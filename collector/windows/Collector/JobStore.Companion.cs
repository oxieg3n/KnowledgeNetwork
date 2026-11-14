using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Collector;

internal sealed partial class JobStore
{
    private readonly bool companionEnabled;
    private void MigrateSchema1(string directory)
    {
        long bytes = (long)Scalar("PRAGMA page_count")! * (long)Scalar("PRAGMA page_size")!;
        if (new DriveInfo(Path.GetPathRoot(Path.GetFullPath(directory))!).AvailableFreeSpace < bytes + 256L * 1024 * 1024)
            throw new RequestError("migration_backup_disk_reserve");
        string backupPath = Path.Combine(directory, "jobs.pre-v2-" + Guid.NewGuid().ToString("N") + ".sqlite");
        using (File.Open(backupPath, FileMode.CreateNew, FileAccess.Write, FileShare.None)) { }
        using (var backup = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = backupPath, Pooling = false }.ToString()))
        {
            backup.Open(); db.BackupDatabase(backup);
            using var check = backup.CreateCommand();
            check.CommandText = "PRAGMA integrity_check";
            if ((string?)check.ExecuteScalar() != "ok") throw new RequestError("migration_backup_integrity_failed");
            check.CommandText = "PRAGMA journal_mode=DELETE"; check.ExecuteScalar();
        }
        string hash;
        using (var stream = new FileStream(backupPath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
        { stream.Flush(true); hash = Convert.ToHexStringLower(SHA256.HashData(stream)); }
        using (var receipt = new FileStream(backupPath + ".json", FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            byte[] data = Encoding.UTF8.GetBytes(Protocol.Encode(new { schema_version = 1, backup_file = Path.GetFileName(backupPath), backup_sha256 = hash }));
            receipt.Write(data); receipt.Flush(true);
        }
        // Backup and receipt are durable before the first source-database mutation.
        Run("PRAGMA synchronous=FULL");
        using var tx = db.BeginTransaction();
        Run("ALTER TABLE jobs ADD COLUMN job_type TEXT NOT NULL DEFAULT 'unknown'; ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0; ALTER TABLE jobs ADD COLUMN lease_hash TEXT; ALTER TABLE jobs ADD COLUMN lease_expires_at TEXT;", tx);
        var types = new List<(string Id, string Type)>();
        using (var cmd = Command("SELECT id,payload FROM jobs", tx))
        using (var reader = cmd.ExecuteReader()) while (reader.Read())
        {
            string type = "unknown";
            try { using var payload = JsonDocument.Parse(reader.GetString(1)); type = payload.RootElement.GetProperty("job_type").GetString() ?? "unknown"; }
            catch (Exception error) when (error is JsonException or InvalidOperationException or KeyNotFoundException) { }
            types.Add((reader.GetString(0), type));
        }
        foreach (var (id, type) in types) Run("UPDATE jobs SET job_type=$type WHERE id=$id", tx, ("$type", type), ("$id", id));
        Run("UPDATE metadata SET value='2' WHERE key='schema_version'", tx);
        tx.Commit();
    }
    private static void ValidateNarration(JsonElement inputs)
    {
        Protocol.Fields(inputs, "text", "segments");
        static string Text(JsonElement item)
        {
            if (item.ValueKind != JsonValueKind.String || item.GetString() is not { } text || string.IsNullOrWhiteSpace(text) ||
                text.EnumerateRunes().Count() > 12000 || text.Any(c => char.IsControl(c) && c is not ('\n' or '\t')))
                throw new RequestError("invalid_narration_text");
            return text;
        }
        string text = Text(inputs.GetProperty("text"));
        if (!inputs.TryGetProperty("segments", out var segments)) return;
        if (segments.ValueKind != JsonValueKind.Array || segments.GetArrayLength() is < 1 or > 16) throw new RequestError("invalid_narration_segments");
        string[] parts = segments.EnumerateArray().Select(Text).ToArray();
        static string Normal(string value) => string.Join(' ', value.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));
        if (parts.Sum(part => part.EnumerateRunes().Count()) > 12000 || Normal(text) != Normal(string.Join(' ', parts)))
            throw new RequestError("invalid_narration_segments");
    }
    private bool MediaHeld(SqliteTransaction? tx = null) => Scalar("SELECT 1 FROM jobs WHERE state='reconciliation_required' LIMIT 1", tx) is not null;
    private void ExpireLeases()
    {
        using var tx = db.BeginTransaction();
        var expired = new List<string>();
        using (var cmd = Command("SELECT id FROM jobs WHERE job_type IN ('narration.generate','editor.operation') AND state='running' AND (lease_expires_at IS NULL OR lease_expires_at <= $now)", tx, ("$now", DateTimeOffset.UtcNow.ToString("O"))))
        using (var reader = cmd.ExecuteReader()) while (reader.Read()) expired.Add(reader.GetString(0));
        foreach (var id in expired)
        {
            Run("UPDATE jobs SET state='reconciliation_required',error='COMPANION_LEASE_EXPIRED',lease_hash=NULL,lease_expires_at=NULL WHERE id=$id", tx, ("$id", id));
            Event(id, "reconciliation_required", "", tx);
        }
        tx.Commit();
    }
    private void RequireCompanion() { if (!companionEnabled) throw new RequestError("companion_disabled"); }
    private object Claim()
    {
        RequireCompanion();
        string? id = null, payload = null, hash = null, expires = null;
        using var tx = db.BeginTransaction();
        if (MediaHeld(tx) || Scalar("SELECT 1 FROM jobs WHERE job_type IN ('narration.generate','editor.operation') AND state='running' LIMIT 1", tx) is not null)
        { tx.Commit(); return new { job = (object?)null, inputs = (object?)null, lease_token = (string?)null }; }
        using (var cmd = Command("SELECT id,payload,payload_hash,expires_at FROM jobs WHERE job_type IN ('narration.generate','editor.operation') AND state='queued' ORDER BY priority DESC,created_at,id LIMIT 1", tx))
        using (var reader = cmd.ExecuteReader()) if (reader.Read()) { id = reader.GetString(0); payload = reader.GetString(1); hash = reader.GetString(2); expires = reader.GetString(3); }
        if (id is null) { tx.Commit(); return new { job = (object?)null, inputs = (object?)null, lease_token = (string?)null }; }
        if (hash != Protocol.Hash(payload!) || DateTimeOffset.Parse(expires!, System.Globalization.CultureInfo.InvariantCulture) <= DateTimeOffset.UtcNow)
        {
            string state = hash != Protocol.Hash(payload!) ? "blocked" : "expired";
            Run("UPDATE jobs SET state=$state,error=$error WHERE id=$id", tx, ("$id", id), ("$state", state), ("$error", state == "blocked" ? "payload_digest_mismatch" : "expired_before_execution"));
            Event(id, state, "", tx); tx.Commit(); return new { job = (object?)null, inputs = (object?)null, lease_token = (string?)null };
        }
        using var document = JsonDocument.Parse(payload!);
        var inputs = document.RootElement.GetProperty("inputs");
        if (document.RootElement.GetProperty("job_type").GetString() == "editor.operation") ValidateEditor(inputs);
        else ValidateNarration(inputs);
        string token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(16));
        Run("UPDATE jobs SET state='running',attempt=attempt+1,lease_hash=$hash,lease_expires_at=$expires WHERE id=$id", tx,
            ("$id", id), ("$hash", Protocol.Hash(token)), ("$expires", DateTimeOffset.UtcNow.AddSeconds(60).ToString("O")));
        Event(id, "companion_claimed", "", tx); tx.Commit();
        return new { job = Get(id), inputs = inputs.Clone(), lease_token = token };
    }
    private string ValidateLease(JsonElement request, SqliteTransaction tx)
    {
        RequireCompanion();
        string id = Protocol.Text(request, "job_id", 32), token = Protocol.Text(request, "lease_token", 32);
        if (id.Length != 32 || !Guid.TryParseExact(id, "N", out _) || token.Length != 32 || token.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c))) throw new RequestError("companion_lease_invalid");
        using var cmd = Command("SELECT lease_hash FROM jobs WHERE id=$id AND job_type IN ('narration.generate','editor.operation') AND state='running'", tx, ("$id", id));
        var stored = cmd.ExecuteScalar() as string;
        if (stored is null || !CryptographicOperations.FixedTimeEquals(Encoding.UTF8.GetBytes(stored), Encoding.UTF8.GetBytes(Protocol.Hash(token))))
            throw new RequestError("companion_lease_invalid");
        return id;
    }
    private object Heartbeat(JsonElement request)
    {
        using var tx = db.BeginTransaction(); string id = ValidateLease(request, tx);
        Run("UPDATE jobs SET lease_expires_at=$expires WHERE id=$id", tx, ("$id", id), ("$expires", DateTimeOffset.UtcNow.AddSeconds(60).ToString("O")));
        bool cancel = (long)Scalar("SELECT cancel_requested FROM jobs WHERE id=$id", tx, ("$id", id))! != 0;
        tx.Commit(); return new { cancel_requested = cancel };
    }
    private object Complete(JsonElement request)
    {
        using var tx = db.BeginTransaction(); string id = ValidateLease(request, tx);
        var result = request.GetProperty("result");
        bool editor = (string?)Scalar("SELECT job_type FROM jobs WHERE id=$id", tx, ("$id", id)) == "editor.operation";
        Protocol.Fields(result, editor ? ["status", "provider", "operation", "publication_eligible", "error", "revision", "native_receipt_sha256"] :
            ["status", "provider", "narrator_id", "publication_eligible", "error", "narration_receipt_sha256", "audio_sha256"]);
        string status = Protocol.Text(result, "status", 32);
        string state = status switch { "completed" => "succeeded", "blocked" or "failed" or "cancelled" or "reconciliation_required" => status, _ => throw new RequestError("invalid_companion_result") };
        if (Protocol.Text(result, "provider", 32) != (editor ? "openshot_native" : "voxcpm2_remote") ||
            (!editor && Protocol.Text(result, "narrator_id", 32) != "oxiegen-narrator") ||
            !result.TryGetProperty("publication_eligible", out var eligible) || eligible.ValueKind != JsonValueKind.False) throw new RequestError("invalid_companion_result");
        if (editor)
        {
            using var payload = JsonDocument.Parse((string)Scalar("SELECT payload FROM jobs WHERE id=$id", tx, ("$id", id))!);
            if (Protocol.Text(result, "operation", 32) != payload.RootElement.GetProperty("inputs").GetProperty("operation").GetString())
                throw new RequestError("invalid_companion_result");
            if ((status == "completed" || result.TryGetProperty("revision", out _)) &&
                (!result.TryGetProperty("revision", out var revision) || revision.ValueKind != JsonValueKind.Number || !revision.TryGetInt64(out long number) || number < 0))
                throw new RequestError("invalid_companion_result");
        }
        string? error = null;
        if (result.TryGetProperty("error", out _))
        {
            error = Protocol.Text(result, "error", 128);
            if (error.Any(c => c is not (>= 'A' and <= 'Z') && c is not (>= '0' and <= '9') && c != '_')) throw new RequestError("invalid_companion_result");
        }
        foreach (string field in editor ? new[] { "native_receipt_sha256" } : ["narration_receipt_sha256", "audio_sha256"])
        {
            if (status != "completed" && !result.TryGetProperty(field, out _)) continue;
            string digest = Protocol.Text(result, field, 64);
            if (digest.Length != 64 || digest.Any(c => !char.IsAsciiHexDigit(c) || char.IsUpper(c))) throw new RequestError("invalid_companion_result");
        }
        string encoded = Protocol.Canonical(result), hash = Protocol.Hash(encoded);
        Run("UPDATE jobs SET state=$state,result=$result,result_hash=$hash,error=$error,lease_hash=NULL,lease_expires_at=NULL WHERE id=$id", tx,
            ("$id", id), ("$state", state), ("$result", encoded), ("$hash", hash), ("$error", (object?)error ?? DBNull.Value));
        Event(id, state, hash, tx); tx.Commit(); return Get(id);
    }
}
