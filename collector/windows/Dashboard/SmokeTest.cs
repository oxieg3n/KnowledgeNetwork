using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Automation.Peers;
using System.Windows.Automation.Provider;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace CollectorDashboard;

public partial class MainWindow
{
    internal async Task<int> SmokeTest(string outputDirectory)
    {
        string output = Path.GetFullPath(outputDirectory);
        if (Directory.Exists(output) || File.Exists(output)) return 2;
        Directory.CreateDirectory(output);
        var checks = new List<object>();
        var elapsed = Stopwatch.StartNew();
        int failures = 0, blocked = 0;
        var buttons = new Dictionary<string, Button>();
        void Check(string name, bool passed, object? evidence = null)
        {
            checks.Add(new { name, status = passed ? "PASS" : "FAILED", elapsed_ms = elapsed.ElapsedMilliseconds, evidence });
            if (!passed) failures++;
        }
        try
        {
            Show();
            Activate();
            await Dispatcher.Yield(DispatcherPriority.ApplicationIdle);
            UpdateLayout();
            foreach (var button in Descendants(this).OfType<Button>())
            {
                string name = AutomationProperties.GetName(button);
                if (name.Length > 0) buttons.Add(name, button);
            }
            Check("shown_native_window", IsVisible && ActualWidth > 0 && ActualHeight > 0);
            Check("named_action_controls", buttons.Count == 6);
            bool focused = Health.Focus();
            Check("programmatic_WPF_focus_health", focused && Keyboard.FocusedElement == Health);
            bool moved = Health.MoveFocus(new TraversalRequest(FocusNavigationDirection.Next));
            string nextName = Keyboard.FocusedElement is DependencyObject next ? AutomationProperties.GetName(next) : "";
            Check("programmatic_WPF_MoveFocus_next", moved && nextName == "Get worker capabilities", nextName);
            var focusOrder = new List<string> { "Check worker health", nextName };
            for (int index = 0; index < 6; index++)
            {
                if (Keyboard.FocusedElement is UIElement current)
                    current.MoveFocus(new TraversalRequest(FocusNavigationDirection.Next));
                focusOrder.Add(Keyboard.FocusedElement is DependencyObject target ? AutomationProperties.GetName(target) : "");
            }
            Check("programmatic_WPF_full_focus_order", focusOrder.SequenceEqual(new[] { "Check worker health", "Get worker capabilities",
                "Get read-only research snapshot", "Run durable diagnostic echo test", "Job ID", "Get entered job status",
                "Request cancellation of entered job", "Raw worker JSON response" }), focusOrder);

            async Task<JsonElement?> Invoke(string name, string expectedStatus, bool optionalSnapshot = false)
            {
                string previous = Status.Text;
                var peer = UIElementAutomationPeer.CreatePeerForElement(buttons[name]) as ButtonAutomationPeer;
                if (peer?.GetPattern(PatternInterface.Invoke) is not IInvokeProvider provider)
                    throw new InvalidOperationException("invoke_provider_missing");
                var requestTime = Stopwatch.StartNew();
                provider.Invoke();
                await Dispatcher.Yield(DispatcherPriority.ApplicationIdle);
                while ((!Actions.IsEnabled || Status.Text == previous) && requestTime.Elapsed < TimeSpan.FromSeconds(45))
                    await Task.Delay(50);
                bool completed = Actions.IsEnabled && Status.Text != previous;
                bool passed = completed && Status.Text.StartsWith(expectedStatus, StringComparison.Ordinal);
                JsonElement? response = null;
                try { using var parsed = JsonDocument.Parse(Response.Text); response = parsed.RootElement.Clone(); }
                catch (JsonException) { }
                if (optionalSnapshot && response is { } s && s.TryGetProperty("ok", out var snapshotOk) && !snapshotOk.GetBoolean() &&
                    s.TryGetProperty("error", out var reason) && reason.GetString() == "research_snapshot_not_configured")
                {
                    blocked++;
                    checks.Add(new { name = "UIA_Invoke_" + name, status = "BLOCKED", completed,
                        duration_ms = requestTime.ElapsedMilliseconds, status_text = Status.Text, response });
                }
                else Check("UIA_Invoke_" + name, passed, new { completed, duration_ms = requestTime.ElapsedMilliseconds,
                    status_text = Status.Text, response });
                return response;
            }

            var health = await Invoke("Check worker health", "Worker replied");
            bool serviceHealthy = health is { } h && h.TryGetProperty("ok", out var ok) && ok.GetBoolean();
            Check("real_health_reply", serviceHealthy, health);
            if (serviceHealthy)
            {
                await Invoke("Get worker capabilities", "Capabilities retrieved");
                await Invoke("Get read-only research snapshot", "Read-only research snapshot retrieved", optionalSnapshot: true);
                await Invoke("Run durable diagnostic echo test", "Durable echo succeeded");
                string id = JobId.Text;
                Check("echo_returned_real_job_id", id.Length == 32 && id.All(char.IsAsciiHexDigit), id);
                await Invoke("Get entered job status", "Job state: succeeded");
                await Invoke("Request cancellation of entered job", "Cancellation request returned job state: succeeded");
                JobId.Text = "invalid";
                await Invoke("Get entered job status", "Request unavailable: enter_32_character_hex_job_id");
                JobId.Text = id;
                await Invoke("Get entered job status", "Job state: succeeded");
            }
            else
            {
                blocked++;
                checks.Add(new { name = "live_worker_flows", status = "BLOCKED", reason = "health_not_verified" });
            }
            foreach (var size in new[] { (1040, 780), (800, 600) })
            {
                Width = size.Item1; Height = size.Item2;
                await Dispatcher.Yield(DispatcherPriority.ApplicationIdle);
                UpdateLayout();
                await Task.Delay(100);
                string file = Path.Combine(output, $"dashboard-{size.Item1}x{size.Item2}.png");
                var bitmap = new RenderTargetBitmap((int)Math.Ceiling(ActualWidth), (int)Math.Ceiling(ActualHeight), 96, 96, PixelFormats.Pbgra32);
                bitmap.Render(this);
                var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
                using (var stream = new FileStream(file, FileMode.CreateNew)) encoder.Save(stream);
                var bounds = buttons.Select(pair => new { name = pair.Key,
                    bounds = pair.Value.TransformToAncestor(this).TransformBounds(new Rect(pair.Value.RenderSize)) }).ToArray();
                Check($"rendered_visual_tree_{size.Item1}x{size.Item2}", File.Exists(file) && Response.ActualHeight >= 40 &&
                    bounds.All(b => b.bounds.Left >= 0 && b.bounds.Top >= 0 && b.bounds.Right <= ActualWidth && b.bounds.Bottom <= ActualHeight),
                    new { file, window_dip_width = ActualWidth, window_dip_height = ActualHeight,
                        image_pixels_width = bitmap.PixelWidth, image_pixels_height = bitmap.PixelHeight, bounds });
            }
        }
        catch (Exception error)
        {
            failures++;
            checks.Add(new { name = "smoke_execution", status = "FAILED", error_type = error.GetType().Name });
        }
        finally
        {
            var report = new { schema_version = 1, status = failures == 0 ? (blocked == 0 ? "PASS" : "BLOCKED") : "FAILED",
                failures, blocked, duration_ms = elapsed.ElapsedMilliseconds, checks,
                method = "Shown real WPF window; actual ButtonAutomationPeer IInvokeProvider; real adjacent CLI and worker; programmatic WPF Focus/MoveFocus",
                capture = "Rendered WPF visual tree via RenderTargetBitmap at96dpi; not an OS desktop screenshot or actual OS DPI-change test",
                not_tested = new[] { "OS key injection", "OS screenshot/compositor", "actual OS DPI scaling", "external computer-use connection", "audio listening" },
                publication_eligible = false };
            await File.WriteAllTextAsync(Path.Combine(output, "smoke-results.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
            Close();
        }
        return failures == 0 ? 0 : 1;
    }

    private static IEnumerable<DependencyObject> Descendants(DependencyObject parent)
    {
        for (int i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            yield return child;
            foreach (var descendant in Descendants(child)) yield return descendant;
        }
    }
}
