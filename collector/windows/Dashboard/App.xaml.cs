using System.Windows;
namespace CollectorDashboard;
public partial class App : Application
{
    private async void OnStartup(object sender, StartupEventArgs e)
    {
        var window = new MainWindow();
        MainWindow = window;
        if (e.Args.Length == 2 && e.Args[0] == "--smoke-test")
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            try { Shutdown(await window.SmokeTest(e.Args[1])); }
            catch (Exception error) when (error is System.IO.IOException or UnauthorizedAccessException or ArgumentException)
            { Shutdown(2); }
        }
        else window.Show();
    }
}
