using System.Diagnostics;
using System.Runtime.InteropServices;

namespace DesktopApp.Services;

/// <summary>
/// Cross-platform desktop notification service.
/// Uses native OS mechanisms without requiring additional NuGet packages.
/// </summary>
public class NotificationService
{
    private bool _enabled = true;

    public bool Enabled
    {
        get => _enabled;
        set => _enabled = value;
    }

    /// <summary>
    /// Show a desktop notification with the given title and body.
    /// Silently no-ops when <see cref="Enabled"/> is false or the platform is unsupported.
    /// </summary>
    public void Show(string title, string body)
    {
        if (!_enabled)
            return;

        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                ShowWindows(title, body);
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
                ShowMacOs(title, body);
            else
                ShowLinux(title, body);
        }
        catch
        {
            // Notifications are best-effort; never crash the app.
        }
    }

    // -----------------------------------------------------------------------
    // Platform implementations
    // -----------------------------------------------------------------------

    private static void ShowWindows(string title, string body)
    {
        // Use PowerShell Toast notification (works on Windows 10/11 without extra packages).
        var escaped_title = title.Replace("'", "''");
        var escaped_body  = body.Replace("'", "''");
        var script = $"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $template.SelectSingleNode('//text[@id=1]').InnerText = '{escaped_title}'
            $template.SelectSingleNode('//text[@id=2]').InnerText = '{escaped_body}'
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('getMediaPlayerInfo').Show($toast)
            """;

        RunProcess("powershell.exe", $"-WindowStyle Hidden -NonInteractive -Command \"{script}\"");
    }

    private static void ShowMacOs(string title, string body)
    {
        var escaped_title = title.Replace("\"", "\\\"");
        var escaped_body  = body.Replace("\"", "\\\"");
        RunProcess("osascript", $"-e 'display notification \"{escaped_body}\" with title \"{escaped_title}\"'");
    }

    private static void ShowLinux(string title, string body)
    {
        RunProcess("notify-send", $"--app-name=getMediaPlayerInfo \"{title}\" \"{body}\"");
    }

    private static void RunProcess(string fileName, string arguments)
    {
        var psi = new ProcessStartInfo
        {
            FileName               = fileName,
            Arguments              = arguments,
            UseShellExecute        = false,
            CreateNoWindow         = true,
            RedirectStandardOutput = true,
            RedirectStandardError  = true,
        };

        using var p = Process.Start(psi);
        p?.WaitForExit(5000);
    }
}
