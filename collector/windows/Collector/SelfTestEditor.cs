using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Collector;

internal static class SelfTestEditor
{
    public static int Run(string root)
    {
        int checks = 0;
        void Check(bool value) { if (!value) throw new InvalidOperationException("editor_assertion_" + checks); checks++; }
        JsonElement Json(object value) => JsonSerializer.Deserialize<JsonElement>(Protocol.Encode(value));
        JsonElement Job(string key, string operation = "inspect", object? request = null, string? session = null) => Json(new
        { schema_version = 1, job_type = "editor.operation", idempotency_key = key,
          inputs = new { session_id = session ?? new string('a', 32), operation, request = request ?? new { } } });
        JsonElement Call(JobStore store, string op, string? id = null, string? token = null, object? result = null)
        {
            var request = new Dictionary<string, object?> { ["schema_version"] = 1, ["operation"] = op };
            if (id is not null) request["job_id"] = id;
            if (token is not null) request["lease_token"] = token;
            if (result is not null) request["result"] = result;
            return Json(store.Dispatch(Json(request)));
        }
        object Done(string operation = "inspect", string status = "completed") => new
        { status, provider = "openshot_native", publication_eligible = false, operation, revision = 7, native_receipt_sha256 = new string('b', 64) };
        void Reject(Action action, string code)
        {
            try { action(); throw new InvalidOperationException("expected_" + code); }
            catch (RequestError error) { Check(error.Message == code); }
        }
        using (var disabled = new JobStore(Path.Combine(root, "disabled")))
        { Reject(() => disabled.Submit(Job("disabled")), "unsupported_job_type"); Check(!Call(disabled, "capabilities").GetProperty("editor_jobs_enabled").GetBoolean()); }
        var directory = Path.Combine(root, "enabled");
        using (var store = new JobStore(directory, enableCompanion: true))
        {
            var capabilities = Call(store, "capabilities");
            Check(capabilities.GetProperty("editor_jobs_enabled").GetBoolean());
            Check(!capabilities.GetProperty("editor_export_jobs_enabled").GetBoolean());
            Check(capabilities.GetProperty("editor_operations").EnumerateArray().Select(value => value.GetString()).SequenceEqual(new[] { "inspect", "apply", "save", "reopen" }));
            foreach (string op in new[] { "start", "close", "undo", "export" }) Reject(() => store.Submit(Job(op, op)), "invalid_editor_operation");
            Reject(() => store.Submit(Job("bad-session", session: "../session")), "invalid_editor_operation");
            Reject(() => store.Submit(Job("extra-inspect", request: new { path = @"C:\private\owned.osp" })), "unexpected_or_duplicate_field");
            Reject(() => store.Submit(Job("relative-save", "save", new { path = "owned.osp" })), "invalid_editor_path");
            Reject(() => store.Submit(Job("unc-save", "save", new { path = @"\\host\share\owned.osp" })), "invalid_editor_path");
            Reject(() => store.Submit(Job("bad-hash", "reopen", new { path = @"C:\private\owned.osp", sha256 = "wrong" })), "invalid_editor_digest");
            Reject(() => store.Submit(Job("negative-revision", "apply", new { base_revision = -1, commands = new object[] { } })), "invalid_editor_revision");
            Reject(() => store.Submit(Job("empty-apply", "apply", new { base_revision = 0, commands = new object[] { } })), "invalid_editor_commands");
            Reject(() => store.Submit(Job("shell", "apply", new { base_revision = 0, commands = new[] { new { method = "shell", @params = new { } } } })), "unsupported_editor_method");
            Reject(() => store.Submit(Job("param-shell", "apply", new { base_revision = 0, commands = new[] { new { method = "clip.remove", @params = new { id = "owned", command = "whoami" } } } })), "unexpected_or_duplicate_field");
            Reject(() => store.Submit(Job("oversized-string", "apply", new { base_revision = 0, commands = new[] { new { method = "clip.remove", @params = new { id = new string('x', 4097) } } } })), "invalid_editor_json");
            var duplicate = JsonSerializer.Deserialize<JsonElement>("""{"schema_version":1,"job_type":"editor.operation","idempotency_key":"duplicate","inputs":{"session_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","operation":"apply","request":{"base_revision":0,"commands":[{"method":"clip.set","params":{"id":"owned","values":{"alpha":0,"alpha":1}}}]}}}""");
            Reject(() => store.Submit(duplicate), "invalid_editor_json");
            object[] commands = [new { method = "text.add", @as = "title", @params = new { text = "Owned title", layer = 3000000, position = 0, duration = 2 } },
                new { method = "clip.set", @params = new { id = new Dictionary<string, string> { ["$ref"] = "title.clip.id" }, values = new { alpha = .5 } } }];
            foreach (var (op, request) in new (string, object)[] {
                ("inspect", new { }), ("apply", new { commands, base_revision = 0 }),
                ("save", new { path = @"C:\private\owned.osp" }), ("reopen", new { path = @"C:\private\owned.osp", sha256 = new string('c', 64) }) })
            {
                string id = Json(store.Submit(Job("valid-" + op, op, request))).GetProperty("job_id").GetString()!;
                store.ExecuteNext(); Check(Json(store.Get(id)).GetProperty("state").GetString() == "queued");
                var claim = Call(store, "companion.claim"); string token = claim.GetProperty("lease_token").GetString()!;
                Check(claim.GetProperty("job").GetProperty("job_type").GetString() == "editor.operation");
                Check(claim.GetProperty("inputs").GetProperty("operation").GetString() == op);
                if (op == "inspect")
                {
                    Reject(() => Call(store, "companion.complete", id, token, Done("save")), "invalid_companion_result");
                    Reject(() => Call(store, "companion.complete", id, token, new { status = "completed", provider = "openshot_native", publication_eligible = false, operation = op, revision = -1, native_receipt_sha256 = new string('b', 64) }), "invalid_companion_result");
                    Reject(() => Call(store, "companion.complete", id, token, new { status = "completed", provider = "openshot_native", publication_eligible = false, operation = op, revision = 7, native_receipt_sha256 = new string('b', 64), native = new { project = "private dump" } }), "unexpected_or_duplicate_field");
                }
                Check(Call(store, "companion.complete", id, token, Done(op)).GetProperty("state").GetString() == "succeeded");
            }
            string editorId = Json(store.Submit(Job("cross-type"))).GetProperty("job_id").GetString()!;
            var active = Call(store, "companion.claim"); string activeToken = active.GetProperty("lease_token").GetString()!;
            store.Submit(Json(new { schema_version = 1, job_type = "narration.generate", idempotency_key = "waiting-narration", inputs = new { text = "Owned body." } }));
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
            Check(Json(store.Cancel(editorId)).GetProperty("state").GetString() == "running");
            Check(Call(store, "companion.heartbeat", editorId, activeToken).GetProperty("cancel_requested").GetBoolean());
            Call(store, "companion.complete", editorId, activeToken, Done(status: "reconciliation_required"));
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
            Check(Call(store, "capabilities").GetProperty("media_reconciliation_hold").GetBoolean());
        }
        string restart = Path.Combine(root, "restart"), restartId;
        using (var store = new JobStore(restart, enableCompanion: true))
        { restartId = Json(store.Submit(Job("restart"))).GetProperty("job_id").GetString()!; Call(store, "companion.claim"); }
        using (var store = new JobStore(restart, enableCompanion: true))
        {
            Check(Json(store.Get(restartId)).GetProperty("state").GetString() == "reconciliation_required");
            Check(Call(store, "companion.claim").GetProperty("job").ValueKind == JsonValueKind.Null);
        }
        string expiry = Path.Combine(root, "expiry");
        using (var store = new JobStore(expiry, enableCompanion: true))
        {
            string id = Json(store.Submit(Job("expiry"))).GetProperty("job_id").GetString()!;
            string token = Call(store, "companion.claim").GetProperty("lease_token").GetString()!;
            using (var db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(expiry, "jobs.sqlite"), Pooling = false }.ToString()))
            { db.Open(); using var cmd = db.CreateCommand(); cmd.CommandText = "UPDATE jobs SET lease_expires_at='2000-01-01T00:00:00Z'"; cmd.ExecuteNonQuery(); }
            Reject(() => Call(store, "companion.complete", id, token, Done()), "companion_lease_invalid");
            Check(Json(store.Get(id)).GetProperty("state").GetString() == "reconciliation_required");
        }
        return checks;
    }
}
