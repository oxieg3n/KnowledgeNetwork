using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;

namespace CollectorDashboard;

internal static class WorkerClient
{
    public static async Task<JsonElement> Call(CancellationToken stopping, params string[] args)
    {
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(stopping);
        timeout.CancelAfter(TimeSpan.FromSeconds(15));
        using var child = new Process { StartInfo = new ProcessStartInfo(
            Path.Combine(AppContext.BaseDirectory, "kn-collector.exe")) {
            UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true,
            RedirectStandardError = true, WorkingDirectory = AppContext.BaseDirectory } };
        foreach (var argument in args) child.StartInfo.ArgumentList.Add(argument);
        child.Start();
        try
        {
            var stdout = Read(child.StandardOutput, timeout.Token);
            var stderr = Read(child.StandardError, timeout.Token);
            await Task.WhenAll(stdout, stderr, child.WaitForExitAsync(timeout.Token));
            using var parsed = JsonDocument.Parse(await stdout, new JsonDocumentOptions { MaxDepth = 32 });
            return parsed.RootElement.Clone();
        }
        finally
        {
            if (!child.HasExited) child.Kill(entireProcessTree: true);
        }
    }
    private static async Task<string> Read(StreamReader stream, CancellationToken token)
    {
        var result = new StringBuilder();
        var buffer = new char[2048];
        int count;
        while ((count = await stream.ReadAsync(buffer.AsMemory(), token)) > 0)
        {
            if (result.Length + count > 65536) throw new InvalidDataException("worker_response_too_large");
            result.Append(buffer, 0, count);
        }
        return result.ToString();
    }
}
