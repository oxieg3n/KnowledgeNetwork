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
        var manifestPath = Path.Combine(path, "files.sha256.json");
        foreach (bool bom in new[] { false, true })
        {
            File.WriteAllText(manifestPath, "[]", new System.Text.UTF8Encoding(bom));
            using var manifest = ServiceInstall.ReadPackageManifest(manifestPath);
            Check(manifest.RootElement.ValueKind == JsonValueKind.Array);
        }
        string Read(byte[] bytes) => Protocol.ReadLine(new MemoryStream(bytes), CancellationToken.None).GetAwaiter().GetResult();
        Check(Read(System.Text.Encoding.UTF8.GetBytes("{}\n")) == "{}");
        Reject(() => Read(System.Text.Encoding.UTF8.GetBytes("{}")), "incomplete_request");
        Reject(() => Read(System.Text.Encoding.UTF8.GetBytes(new string('x', Protocol.MaxBytes + 1) + "\n")), "request_too_large");
        try { Read([0xc3, 0x28, 10]); throw new InvalidOperationException("invalid_utf8_accepted"); }
        catch (System.Text.DecoderFallbackException) { checks++; }
        var foreign = Path.Combine(path, "future-schema"); Directory.CreateDirectory(foreign);
        var foreignDatabase = Path.Combine(foreign, "jobs.sqlite");
        using (var connection = new SqliteConnection("Data Source=" + foreignDatabase + ";Pooling=False"))
        {
            connection.Open(); using var cmd = connection.CreateCommand();
            cmd.CommandText = "CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); INSERT INTO metadata VALUES('schema_version','3')";
            cmd.ExecuteNonQuery();
        }
        var foreignBytes = File.ReadAllBytes(foreignDatabase);
        Reject(() => { using var rejected = new JobStore(foreign); }, "unsupported_database_schema");
        Check(File.ReadAllBytes(foreignDatabase).SequenceEqual(foreignBytes));
        var job = Json("""{"schema_version":1,"job_type":"diagnostic.echo","idempotency_key":"test-1","inputs":{"nonce":"hello"}}""");
        string id, worker;
        using (var store = new JobStore(path))
        {
            worker = store.WorkerId;
            id = Value(store.Submit(job)).GetProperty("job_id").GetString()!;
            Check(Value(store.Submit(job)).GetProperty("job_id").GetString() == id);
            Check(Value(store.Submit(Json("""{"inputs":{"nonce":"\u0068ello"},"idempotency_key":"test-1","job_type":"diagnostic.echo","schema_version":1}"""))).GetProperty("job_id").GetString() == id);
            Reject(() => store.Submit(Json(job.GetRawText().Replace("hello", "different"))), "idempotency_conflict");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("diagnostic.echo", "shell"))), "unsupported_job_type");
            Reject(() => store.Submit(Json(job.GetRawText().Replace("diagnostic.echo", "narration.generate"))), "unsupported_job_type");
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
        using (var store = new JobStore(path))
        using (var connection = new SqliteConnection("Data Source=" + Path.Combine(path, "jobs.sqlite")))
        {
            connection.Open(); using var cmd = connection.CreateCommand();
            var tampered = Value(store.Submit(Json(job.GetRawText().Replace("test-1", "tampered-1")))).GetProperty("job_id").GetString()!;
            cmd.CommandText = "UPDATE jobs SET payload='{}' WHERE id=$id"; cmd.Parameters.AddWithValue("$id", tampered); cmd.ExecuteNonQuery();
            store.ExecuteNext();
            Check(Value(store.Get(tampered)).GetProperty("error").GetString() == "payload_digest_mismatch");
            cmd.CommandText = "UPDATE jobs SET result='{}' WHERE id=$id"; cmd.Parameters["$id"].Value = id; cmd.ExecuteNonQuery();
            Reject(() => store.Get(id), "result_digest_mismatch");
        }
        checks += SelfTestCompanion.Run(Path.Combine(path, "companion"));
        // Evidence remains in a uniquely named temporary directory for the coordinator to inspect.
        Console.WriteLine(Protocol.Encode(new { status = "PASS", checks, evidence_directory = path }));
    }
}
