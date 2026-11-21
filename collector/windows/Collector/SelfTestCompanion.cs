using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Collector;

internal static class SelfTestCompanion
{
    public static int Run(string root)
    {
        int checks = 0;
        void Check(bool condition) { if (!condition) throw new InvalidOperationException("companion_assertion_" + checks); checks++; }
        JsonElement Json(object value) => JsonSerializer.Deserialize<JsonElement>(Protocol.Encode(value));
        JsonElement Call(JobStore store, string op, string? id = null, string? token = null, object? result = null)
        {
            var request = new Dictionary<string, object?> { ["schema_version"] = 1, ["operation"] = op };
            if (id is not null) request["job_id"] = id;
            if (token is not null) request["lease_token"] = token;
            if (result is not null) request["result"] = result;
            return Json(store.Dispatch(Json(request)));
        }
        JsonElement Job(string key, string text = "First.\nSecond.", string[]? segments = null) =>
            Json(new { schema_version = 1, job_type = "narration.generate", idempotency_key = key,
                inputs = segments is null ? (object)new { text } : new { text, segments } });
        void Reject(Action action, string code)
        {
            try { action(); throw new InvalidOperationException("expected_" + code); }
            catch (RequestError error) { Check(error.Message == code); }
        }
        object Result(string status = "completed", string? error = null) => status == "completed"
            ? new { status, provider = "voxcpm2_remote", narrator_id = "oxiegen-narrator", publication_eligible = false,
                    narration_receipt_sha256 = new string('a', 64), audio_sha256 = new string('b', 64) }
            : new { status, provider = "voxcpm2_remote", narrator_id = "oxiegen-narrator", publication_eligible = false, error };
        Check(Program.ParseInstallArguments([]) == (null, null));
        Check(Program.ParseInstallArguments(["--enable-companion"]).CompanionOverride == true);
        Check(Program.ParseInstallArguments(["S-1-5-21-1-2-3-1001", "--disable-companion"]) == ("S-1-5-21-1-2-3-1001", false));
        Reject(() => Program.ParseInstallArguments(["--other"]), "invalid_install_arguments");
        Reject(() => Program.ParseInstallArguments(["--enable-companion", "--enable-companion"]), "duplicate_or_conflicting_install_flag");
        Reject(() => Program.ParseInstallArguments(["--enable-companion", "--disable-companion"]), "duplicate_or_conflicting_install_flag");
        Reject(() => Program.ParseInstallArguments(["S-1-5-21-1-2-3-1001", "S-1-5-21-1-2-3-1002"]), "invalid_install_arguments");
        void Sql(string directory, string sql)
        {
            using var db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(directory, "jobs.sqlite"), Pooling = false }.ToString());
            db.Open(); using var cmd = db.CreateCommand(); cmd.CommandText = sql; cmd.ExecuteNonQuery();
        }
        using (var store = new JobStore(Path.Combine(root, "disabled")))
        {
            Reject(() => store.Submit(Job("disabled")), "unsupported_job_type");
            Reject(() => Call(store, "companion.claim"), "companion_disabled");
            Check(!Call(store, "capabilities").GetProperty("narration_jobs_enabled").GetBoolean());
        }
        var normal = Path.Combine(root, "normal");
        using (var store = new JobStore(normal, enableCompanion: true))
        {
            var input = Job("typed-1", segments: ["First.", "Second."]);
            string id = Json(store.Submit(input)).GetProperty("job_id").GetString()!;
            Check(Json(store.Submit(input)).GetProperty("job_id").GetString() == id);
            Reject(() => store.Submit(Job("typed-1", "Changed.")), "idempotency_conflict");
            Reject(() => store.Submit(Job("oversize", new string('x', 12001))), "invalid_narration_text");
            Reject(() => store.Submit(Job("segments", "First. Second.", ["Different."])), "invalid_narration_segments");
            Reject(() => store.Submit(Job("controls", "Private\0text")), "invalid_narration_text");
            Reject(() => store.Submit(Json(new { schema_version = 1, job_type = "narration.generate", idempotency_key = "shell", inputs = new { text = "Owned.", command = "whoami" } })), "unexpected_or_duplicate_field");
            store.ExecuteNext(); Check(Json(store.Get(id)).GetProperty("state").GetString() == "queued");
            JsonElement[] claims = new JsonElement[2];
            // Incoming owner-pipe callers share the same serialized database writer.
            Parallel.For(0, 2, index => { lock (store) claims[index] = Call(store, "companion.claim"); });
            Check(claims.Count(claim => claim.GetProperty("job").ValueKind != JsonValueKind.Null) == 1);
            var claim = claims.Single(item => item.GetProperty("job").ValueKind != JsonValueKind.Null);
            string token = claim.GetProperty("lease_token").GetString()!;
            Check(token.Length == 32 && claim.GetProperty("job").GetProperty("job_type").GetString() == "narration.generate");
            Check(claim.GetProperty("inputs").GetProperty("text").GetString() == "First.\nSecond.");
            Check(!Protocol.Encode(store.Get(id)).Contains(token, StringComparison.Ordinal));
            Check(!Protocol.Encode(store.Get(id)).Contains("First.", StringComparison.Ordinal));
            Reject(() => Call(store, "companion.heartbeat", id, new string('0', 32)), "companion_lease_invalid");
            Check(!Call(store, "companion.heartbeat", id, token).GetProperty("cancel_requested").GetBoolean());
            Check(Json(store.Cancel(id)).GetProperty("state").GetString() == "running");
            Check(Call(store, "companion.heartbeat", id, token).GetProperty("cancel_requested").GetBoolean());
            Reject(() => Call(store, "companion.complete", id, token, new { status = "completed", provider = "voxcpm2_remote", narrator_id = "oxiegen-narrator", publication_eligible = false, path = "private" }), "unexpected_or_duplicate_field");
            Reject(() => Call(store, "companion.complete", id, token, Result("blocked", "Private path")), "invalid_companion_result");
            Reject(() => Call(store, "companion.complete", id, token, new { status = "failed", provider = "voxcpm2_remote", narrator_id = "oxiegen-narrator", publication_eligible = true }), "invalid_companion_result");
            var done = Call(store, "companion.complete", id, token, Result());
            Check(done.GetProperty("state").GetString() == "succeeded");
            Check(!done.GetProperty("result").GetProperty("publication_eligible").GetBoolean());
            Reject(() => Call(store, "companion.complete", id, token, Result()), "companion_lease_invalid");
            string unicode = string.Concat(Enumerable.Repeat("\U0001f600", 12000));
            string unicodeId = Json(store.Submit(Job("unicode", unicode, [unicode]))).GetProperty("job_id").GetString()!;
            var large = Call(store, "companion.claim");
            byte[] frame = Encoding.UTF8.GetBytes(large.GetRawText() + "\n");
            Check(frame.Length > 65536 && frame.Length <= Protocol.MaxBytes);
            using var stream = new MemoryStream(frame);
            Check(Protocol.ReadLine(stream, CancellationToken.None).GetAwaiter().GetResult() == large.GetRawText());
            Call(store, "companion.complete", unicodeId, large.GetProperty("lease_token").GetString(), Result("cancelled", "HOST_CANCELLED"));
            string queued = Json(store.Submit(Job("queued-cancel"))).GetProperty("job_id").GetString()!;
            Check(Json(store.Cancel(queued)).GetProperty("state").GetString() == "cancelled");
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
        }
        string stale = Path.Combine(root, "stale"), staleId, staleToken;
        using (var store = new JobStore(stale, enableCompanion: true))
        {
            staleId = Json(store.Submit(Job("stale"))).GetProperty("job_id").GetString()!;
            staleToken = Call(store, "companion.claim").GetProperty("lease_token").GetString()!;
            Sql(stale, "UPDATE jobs SET lease_expires_at='2000-01-01T00:00:00Z'");
            Reject(() => Call(store, "companion.heartbeat", staleId, staleToken), "companion_lease_invalid");
            Check(Json(store.Get(staleId)).GetProperty("state").GetString() == "reconciliation_required");
            Reject(() => Call(store, "companion.complete", staleId, staleToken, Result()), "companion_lease_invalid");
            store.Submit(Job("different-key"));
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
            var echo = Json(new { schema_version = 1, job_type = "diagnostic.echo", idempotency_key = "read-only", inputs = new { nonce = "still healthy" } });
            string echoId = Json(store.Submit(echo)).GetProperty("job_id").GetString()!;
            store.ExecuteNext(); Check(Json(store.Get(echoId)).GetProperty("state").GetString() == "succeeded");
        }
        using (var store = new JobStore(stale, enableCompanion: true)) Check(Call(store, "capabilities").GetProperty("media_reconciliation_hold").GetBoolean());
        string restart = Path.Combine(root, "restart"), restartedId;
        using (var store = new JobStore(restart, enableCompanion: true))
        { restartedId = Json(store.Submit(Job("restart"))).GetProperty("job_id").GetString()!; Call(store, "companion.claim"); }
        using (var store = new JobStore(restart, enableCompanion: true))
        {
            Check(Json(store.Get(restartedId)).GetProperty("state").GetString() == "reconciliation_required");
            Check(Json(store.Get(restartedId)).GetProperty("attempt").GetInt32() == 1);
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
        }
        using (var store = new JobStore(Path.Combine(root, "known-outcomes"), enableCompanion: true))
        {
            foreach (string state in new[] { "blocked", "failed", "reconciliation_required" })
            {
                string id = Json(store.Submit(Job(state))).GetProperty("job_id").GetString()!;
                string token = Call(store, "companion.claim").GetProperty("lease_token").GetString()!;
                Check(Call(store, "companion.complete", id, token, Result(state, "KNOWN_TEST_STATUS")).GetProperty("state").GetString() == state);
            }
            store.Submit(Job("new-key-cannot-bypass-hold"));
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
        }
        string migration = Path.Combine(root, "migration"); Directory.CreateDirectory(migration);
        string oldId = new('1', 32), oldWorker = new('2', 32);
        using (var legacy = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(migration, "jobs.sqlite"), Pooling = false }.ToString()))
        {
            legacy.Open(); using var cmd = legacy.CreateCommand();
            cmd.CommandText = """
                PRAGMA journal_mode=WAL;
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE jobs(id TEXT PRIMARY KEY,idem TEXT UNIQUE,payload_hash TEXT,payload TEXT,state TEXT,priority INTEGER,created_at TEXT,expires_at TEXT,attempt INTEGER DEFAULT 0,result TEXT,result_hash TEXT,error TEXT);
                CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,state TEXT,at TEXT,digest TEXT);
                INSERT INTO metadata VALUES('schema_version','1');
                INSERT INTO metadata VALUES('worker_id',$worker);
                INSERT INTO jobs(id,idem,payload_hash,payload,state,priority,created_at,expires_at) VALUES($id,'legacy',$hash,$payload,'running',0,$now,$later);
                INSERT INTO events(job_id,state,at,digest) VALUES($id,'legacy_event',$now,$hash);
                """;
            string payload = Protocol.Encode(new { schema_version = 1, job_type = "diagnostic.echo", idempotency_key = "legacy", inputs = new { nonce = "legacy" } });
            foreach (var pair in new[] { ("$id", oldId), ("$worker", oldWorker), ("$hash", Protocol.Hash(payload)), ("$payload", payload), ("$now", DateTimeOffset.UtcNow.ToString("O")), ("$later", DateTimeOffset.UtcNow.AddHours(1).ToString("O")) }) cmd.Parameters.AddWithValue(pair.Item1, pair.Item2);
            cmd.ExecuteNonQuery();
            using (var store = new JobStore(migration))
            {
                Check(store.WorkerId == oldWorker);
                Check(Json(store.Get(oldId)).GetProperty("state").GetString() == "queued");
                store.ExecuteNext(); Check(Json(store.Get(oldId)).GetProperty("state").GetString() == "succeeded");
            }
        }
        string backupPath = Directory.GetFiles(migration, "jobs.pre-v2-*.sqlite").Single();
        using (var backup = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = backupPath, Pooling = false }.ToString()))
        {
            backup.Open(); using var cmd = backup.CreateCommand(); cmd.CommandText = "SELECT value FROM metadata WHERE key='schema_version'";
            Check((string?)cmd.ExecuteScalar() == "1");
            cmd.CommandText = "SELECT state FROM jobs"; Check((string?)cmd.ExecuteScalar() == "running");
            cmd.CommandText = "PRAGMA integrity_check"; Check((string?)cmd.ExecuteScalar() == "ok");
        }
        using var backupReceipt = JsonDocument.Parse(File.ReadAllText(backupPath + ".json"));
        Check(backupReceipt.RootElement.GetProperty("backup_sha256").GetString() == Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(backupPath))));
        string rollback = Path.Combine(root, "migration-rollback"); Directory.CreateDirectory(rollback);
        File.Copy(backupPath, Path.Combine(rollback, "jobs.sqlite"));
        Sql(rollback, "CREATE TRIGGER reject_migration BEFORE UPDATE ON metadata WHEN NEW.value='2' BEGIN SELECT RAISE(ABORT,'fault_injection'); END");
        try { using var rejected = new JobStore(rollback); throw new InvalidOperationException("migration_fault_not_rejected"); }
        catch (SqliteException) { checks++; }
        using (var db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(rollback, "jobs.sqlite"), Pooling = false }.ToString()))
        {
            db.Open(); using var cmd = db.CreateCommand(); cmd.CommandText = "SELECT value FROM metadata WHERE key='schema_version'";
            Check((string?)cmd.ExecuteScalar() == "1");
            cmd.CommandText = "SELECT count(*) FROM pragma_table_info('jobs') WHERE name='job_type'";
            Check((long)cmd.ExecuteScalar()! == 0);
        }
        Check(Directory.GetFiles(rollback, "jobs.pre-v2-*.sqlite").Length == 1);
        using var identity = WindowsIdentity.GetCurrent();
        var unsafeAcl = new FileSecurity(); unsafeAcl.SetSecurityDescriptorSddlForm("O:" + identity.User!.Value + "D:NO_ACCESS_CONTROL");
        Reject(() => Program.ValidatePrivateCompanionAcl(unsafeAcl, identity.User), "private_companion_file_required");
        var ownerRights = new FileSecurity(); ownerRights.SetSecurityDescriptorSddlForm("O:BAD:(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;OW)");
        Program.ValidatePrivateCompanionAcl(ownerRights, identity.User); checks++;
        var foreignOwner = new FileSecurity(); foreignOwner.SetSecurityDescriptorSddlForm("O:S-1-5-21-1-2-3-9999D:(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;OW)");
        Reject(() => Program.ValidatePrivateCompanionAcl(foreignOwner, identity.User), "private_companion_file_required");
        var publicOwnerRights = new FileSecurity(); publicOwnerRights.SetSecurityDescriptorSddlForm("O:BAD:(A;;FA;;;OW)(A;;FR;;;WD)");
        Reject(() => Program.ValidatePrivateCompanionAcl(publicOwnerRights, identity.User), "private_companion_file_required");
        Check(Program.ValidatePrivateCompanionPath(@"C:\private\lease.json") == @"C:\private\lease.json");
        foreach (string path in new[] { @"\\server\share\lease.json", @"\\?\C:\private\lease.json", @"\\.\C:\private\lease.json", @"\??\C:\private\lease.json", "//server/share/lease.json", "lease.json" })
            Reject(() => Program.ValidatePrivateCompanionPath(path), "private_companion_file_required");
        return checks;
    }
}
