using System.Diagnostics;
using System.IO.Pipes;
using System.Text;

namespace Collector;

internal static class SelfTestFrames
{
    private sealed class Fragmented(byte[] bytes) : MemoryStream(bytes)
    {
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default) =>
            base.ReadAsync(buffer[..Math.Min(3, buffer.Length)], token);
    }
    public static int Run(string evidenceDirectory)
    {
        int checks = 0;
        void Check(bool condition) { if (!condition) throw new InvalidOperationException("frame_assertion_" + checks); checks++; }
        string Read(Stream stream) => Protocol.ReadLine(stream, CancellationToken.None).GetAwaiter().GetResult();
        using (var fragmented = new Fragmented(Encoding.UTF8.GetBytes("α😀雪\n"))) Check(Read(fragmented) == "α😀雪");
        using (var maximum = new MemoryStream(Encoding.UTF8.GetBytes(new string('x', Protocol.MaxBytes) + "\n"))) Check(Read(maximum).Length == Protocol.MaxBytes);
        using (var first = new MemoryStream(Encoding.UTF8.GetBytes("{}\nnot another operation\n"))) Check(Read(first) == "{}");
        foreach (var (bytes, error) in new[] {
            (Encoding.UTF8.GetBytes(new string('x', Protocol.MaxBytes + 1) + "\n"), "request_too_large"),
            (Encoding.UTF8.GetBytes(new string('x', 8192)), "incomplete_request") })
        {
            using var stream = new Fragmented(bytes);
            try { Read(stream); throw new InvalidOperationException("expected_" + error); }
            catch (RequestError actual) { Check(actual.Message == error); }
        }
        using (var invalid = new Fragmented([0xf0, 0x28, 0x8c, 0xbc, 10]))
        {
            try { Read(invalid); throw new InvalidOperationException("invalid_fragmented_utf8_accepted"); }
            catch (DecoderFallbackException) { checks++; }
        }
        PipeBenchmark().GetAwaiter().GetResult(); checks++;
        return checks;

        async Task PipeBenchmark()
        {
            string name = "KnowledgeNetworkCollector-selftest-" + Guid.NewGuid().ToString("N");
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            using var server = new NamedPipeServerStream(name, PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
                PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly, 4096, 4096);
            using var client = new NamedPipeClientStream(".", name, PipeDirection.InOut, PipeOptions.Asynchronous);
            var watch = Stopwatch.StartNew();
            var accept = server.WaitForConnectionAsync(deadline.Token);
            await client.ConnectAsync(deadline.Token); await accept;
            byte[] frame = Encoding.UTF8.GetBytes(new string('x', 300084) + "\n");
            var write = client.WriteAsync(frame, deadline.Token).AsTask();
            var read = Protocol.ReadLine(server, deadline.Token);
            await Task.WhenAll(write, read);
            if (read.Result.Length != 300084) throw new InvalidOperationException("large_native_pipe_frame_changed");
            watch.Stop();
            File.WriteAllText(Path.Combine(evidenceDirectory, "pipe-frame-benchmark.json"),
                Protocol.Encode(new { frame_bytes = frame.Length, elapsed_milliseconds = watch.Elapsed.TotalMilliseconds,
                    deadline_seconds = 5, transport = "isolated_unique_current_user_named_pipe", status = "PASS" }));
        }
    }
}
