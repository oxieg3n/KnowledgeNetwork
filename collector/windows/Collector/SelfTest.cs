using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace Collector;

internal static class SelfTest
{
    public static void Run()
    {
        var path = Path.Combine(Path.GetTempPath(), "kn-collector-self-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        int checks = 0;
        void Check(bool condition) { if (!condition) throw new InvalidOperationException("self_test_assertion_" + checks); checks++; }
        JsonElement Json(string raw) => JsonSerializer.Deserialize<JsonElement>(raw);
        JsonElement Value(object value) => Json(Protocol.Encode(value));
        void Reject(Action action, string code)
        {
            try { action(); throw new InvalidOperationException("expected_" + code); }
            catch (RequestError error) { Check(error.Message == code); }
        }
        var job = Json("""{"schema_version":1,"job_type":"diagnostic.echo","idempotency_key":"test-1","inputs":{"nonce":"hello"}}""");
        string id, worker;
        using (var store = new JobStore(path))
        {
            worker = store.WorkerId;
            id = Value(store.Submit(job)).GetProperty("job_id").GetString()!;
            Check(Value(store.Submit(job)).GetProperty("job_id").GetString() == id);
            Reject(() => store.Submit(Json(job.GetRawText().Replace("hello", "different"))), "idempotency_conflict");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("diagnostic.echo", "shell"))), "unsupported_job_type");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("\"nonce\":", "\"shell\":\"whoami\",\"nonce\":"))), "unexpected_or_duplicate_field");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("\"nonce\":", "\"nonce\":\"duplicate\",\"nonce\":"))), "unexpected_or_duplicate_field");
            Reject(() => store.Dispatch(Json("""{"schema_version":1,"operation":"publication.request"}""")), "unsupported_operation");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("\"inputs\":", "\"priority\":99,\"inputs\":"))), "invalid_priority");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("test-1", "expired-1").Replace("\"inputs\":", "\"expires_at\":\"2000-01-01T00:00:00Z\",\"inputs\":"))), "expired_or_invalid_job_window");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("test-1", "badcreated-1").Replace("\"inputs\":", "\"created_at\":\"2026-01-01T00:00:00\",\"inputs\":"))), "invalid_created_at");
            store.ExecuteNext();
            var done = Value(store.Get(id));
            Check(done.GetProperty("state").GetString() == "succeeded");
            Check(done.GetProperty("result").GetProperty("nonce").GetString() == "hello");
            Check(done.GetProperty("result_sha256").GetString() == Protocol.Hash(done.GetProperty("result").GetRawText()));
            Check(done.GetProperty("publication_eligible").GetBoolean() == false);
            var cancelled = Value(store.Submit(Json(job.GetRawText().Replace("test-1", "cancel-me")))).GetProperty("job_id").GetString()!;
            Check(Value(store.Cancel(cancelled)).GetProperty("state").GetString() == "cancelled");
            Check(Value(store.Cancel(id)).GetProperty("state").GetString() == "succeeded");
            var snapshotJob = Json("""{"schema_version":1,"job_type":"research.snapshot","idempotency_key":"snapshot-unconfigured","inputs":{}}""");
            var snapshotId = Value(store.Submit(snapshotJob)).GetProperty("job_id").GetString()!;
            store.ExecuteNext(); Check(Value(store.Get(snapshotId)).GetProperty("state").GetString() == "blocked");
        }
        using (var store = new JobStore(path))
        {
            Check(store.WorkerId == worker);
            Check(Value(store.Get(id)).GetProperty("state").GetString() == "succeeded");
            Check(Value(store.Submit(job)).GetProperty("job_id").GetString() == id);
        }
        using (var connection = new SqliteConnection("Data Source=" + Path.Combine(path, "jobs.sqlite")))
        {
            connection.Open(); using var cmd = connection.CreateCommand();
            cmd.CommandText = "UPDATE jobs SET state='running' WHERE id=$id"; cmd.Parameters.AddWithValue("$id", id); cmd.ExecuteNonQuery();
            cmd.CommandText = "DELETE FROM events";
            try { cmd.ExecuteNonQuery(); throw new InvalidOperationException("journal_not_protected"); }
            catch (SqliteException) { checks++; }
        }
        using (var store = new JobStore(path))
        {
            Check(Value(store.Get(id)).GetProperty("state").GetString() == "queued");
            store.ExecuteNext(); Check(Value(store.Get(id)).GetProperty("state").GetString() == "succeeded");
        }
        var snapshotPath = Path.Combine(path, "research.json");
        const string snapshot = """{"schema_version":1,"revision":7,"control":{"publication_paused":true},"queues":{"FRESH_UPLOAD":{"stable-id":{}},"DAILY_TECH_RECAP":{},"BLOG_VIDEO":{},"EVERGREEN_TOP10":{}}}""";
        File.WriteAllText(snapshotPath, snapshot);
        using (var store = new JobStore(path, snapshotPath, Protocol.Hash(snapshot)))
        {
            var report = Value(store.Dispatch(Json("""{"schema_version":1,"operation":"research.snapshot"}""")));
            Check(report.GetProperty("source_publication_paused").GetBoolean());
            Check(report.GetProperty("queues").GetProperty("FRESH_UPLOAD").GetProperty("count").GetInt32() == 1);
            File.AppendAllText(snapshotPath, " ");
            Reject(() => store.Dispatch(Json("""{"schema_version":1,"operation":"research.snapshot"}""")), "research_snapshot_digest_mismatch");
        }
        // Evidence remains in a uniquely named temporary directory for the coordinator to inspect.
        Console.WriteLine(Protocol.Encode(new { status = "PASS", checks, evidence_directory = path }));
    }
}
