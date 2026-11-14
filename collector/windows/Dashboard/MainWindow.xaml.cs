using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Automation.Peers;

namespace CollectorDashboard;

public partial class MainWindow : Window
{
    private readonly CancellationTokenSource stopping = new();
    public MainWindow() => InitializeComponent();
    private void OnLoaded(object sender, RoutedEventArgs e) => Health.Focus();
    private void OnClosed(object? sender, EventArgs e) => stopping.Cancel();
    private void Tell(string text)
    {
        Status.Text = text;
        UIElementAutomationPeer.FromElement(Status)?.RaiseAutomationEvent(AutomationEvents.LiveRegionChanged);
    }
    private async Task<JsonElement> Request(params string[] args)
    {
        var envelope = await WorkerClient.Call(stopping.Token, args);
        Response.Text = JsonSerializer.Serialize(envelope, new JsonSerializerOptions { WriteIndented = true });
        if (!envelope.GetProperty("ok").GetBoolean())
        {
            var code = envelope.GetProperty("error").GetString();
            throw new InvalidDataException(code is { Length: <= 128 } && code.All(c => char.IsAsciiLetterOrDigit(c) || c == '_') ? code : "worker_request_failed");
        }
        return envelope.GetProperty("result").Clone();
    }
    private async Task Run(Func<Task<string>> action)
    {
        Actions.IsEnabled = false;
        Tell("Request in progress…");
        try { Tell(await action()); }
        catch (Exception error) when (error is IOException or JsonException or InvalidOperationException or
            KeyNotFoundException or OperationCanceledException or System.ComponentModel.Win32Exception)
        {
            string code = error is InvalidDataException ? error.Message : error.GetType().Name;
            Tell($"Request unavailable: {code}. Verify the worker is running, then check health or get the existing job. Accepted jobs continue independently.");
        }
        finally { Actions.IsEnabled = true; }
    }
    private async void HealthClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        string nonce = Guid.NewGuid().ToString("N");
        var result = await Request("health", nonce);
        if (result.GetProperty("nonce").GetString() != nonce) throw new InvalidDataException("health_nonce_mismatch");
        bool paused = result.GetProperty("publication_paused").GetBoolean();
        return $"Worker replied at {DateTimeOffset.Now:t}. Worker ID: {result.GetProperty("worker_id").GetString()}. Publication paused: {paused}.";
    });
    private async void CapabilitiesClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        await Request("capabilities"); return "Capabilities retrieved from the worker. See its exact supported operations below.";
    });
    private async void ResearchClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        await Request("research-snapshot"); return "Read-only research snapshot retrieved. This does not activate a production scheduler.";
    });
    private string ExistingJob()
    {
        string id = JobId.Text.Trim();
        if (id.Length != 32 || !id.All(char.IsAsciiHexDigit)) throw new InvalidDataException("enter_32_character_hex_job_id");
        return id;
    }
    private async void GetClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        var result = await Request("get", ExistingJob());
        return "Job state: " + result.GetProperty("state").GetString() + ".";
    });
    private async void CancelClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        var result = await Request("cancel", ExistingJob());
        return "Cancellation request returned job state: " + result.GetProperty("state").GetString() + ".";
    });
    private async void EchoClick(object sender, RoutedEventArgs e) => await Run(async () =>
    {
        string nonce = Guid.NewGuid().ToString("N");
        string directory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "KnowledgeNetworkCollector", "dashboard-requests");
        Directory.CreateDirectory(directory);
        string file = Path.Combine(directory, nonce + ".json");
        var job = new { schema_version = 1, job_type = "diagnostic.echo", idempotency_key = "dashboard-" + nonce,
            created_at = DateTimeOffset.UtcNow.ToString("O"), expires_at = DateTimeOffset.UtcNow.AddHours(1).ToString("O"),
            priority = 0, inputs = new { nonce } };
        await using (var stream = new FileStream(file, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        { await JsonSerializer.SerializeAsync(stream, job, cancellationToken: stopping.Token); stream.Flush(flushToDisk: true); }
        var result = await Request("submit", file);
        JobId.Text = result.GetProperty("job_id").GetString()!;
        for (int attempt = 0; attempt < 10; attempt++)
        {
            result = await Request("get", JobId.Text);
            string? state = result.GetProperty("state").GetString();
            if (state == "succeeded")
            {
                if (result.GetProperty("result").GetProperty("nonce").GetString() != nonce) throw new InvalidDataException("echo_nonce_mismatch");
                return "Durable echo succeeded with the exact submitted nonce. Job ID: " + JobId.Text + ".";
            }
            if (state is "blocked" or "cancelled" or "expired") return "Echo job state: " + state + ". See the worker response.";
            await Task.Delay(300, stopping.Token);
        }
        return "Echo is still pending. Use Get job to reconcile this job; do not resubmit it.";
    });
}
