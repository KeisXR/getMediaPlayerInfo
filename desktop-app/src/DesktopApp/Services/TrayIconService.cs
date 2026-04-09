using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using DesktopApp.Models;

namespace DesktopApp.Services;

/// <summary>
/// Manages the system-tray icon tooltip text.
/// Actual tray icon UI is declared in App.axaml; this service provides the
/// bridge to update its tooltip from the ViewModel layer.
/// </summary>
public class TrayIconService
{
    private string _tooltip = "getMediaPlayerInfo";

    public string Tooltip
    {
        get => _tooltip;
        private set => _tooltip = value;
    }

    public event EventHandler<string>? TooltipChanged;

    public void UpdateMedia(MediaInfo? media)
    {
        if (media is null || string.IsNullOrWhiteSpace(media.Title))
        {
            SetTooltip("getMediaPlayerInfo — No media");
        }
        else
        {
            var statusIcon = media.Status switch
            {
                PlaybackStatus.Playing => "▶",
                PlaybackStatus.Paused  => "⏸",
                PlaybackStatus.Stopped => "⏹",
                _                      => "●",
            };

            var text = string.IsNullOrWhiteSpace(media.Artist)
                ? $"{statusIcon} {media.Title}"
                : $"{statusIcon} {media.Title} — {media.Artist}";

            // Truncate for OS tooltip limits (~64 chars on some platforms)
            if (text.Length > 63)
                text = text[..60] + "…";

            SetTooltip(text);
        }
    }

    private void SetTooltip(string text)
    {
        if (_tooltip == text)
            return;
        _tooltip = text;
        TooltipChanged?.Invoke(this, text);
    }

    // -----------------------------------------------------------------------
    // OS Startup registration
    // -----------------------------------------------------------------------

    /// <summary>Register or deregister the app to start with the OS.</summary>
    public static void SetStartupRegistration(bool enable)
    {
        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                SetStartupWindows(enable);
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                SetStartupLinux(enable);
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
                SetStartupMacOs(enable);
        }
        catch
        {
            // Best-effort; silently ignore failures
        }
    }

    [SupportedOSPlatform("windows")]
    private static void SetStartupWindows(bool enable)
    {
        const string RegKey = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Run";
        const string AppName = "getMediaPlayerInfo";

        using var key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(RegKey, writable: true);
        if (key is null)
            return;

        if (enable)
        {
            var exe = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? string.Empty;
            key.SetValue(AppName, $"\"{exe}\" --minimized");
        }
        else
        {
            key.DeleteValue(AppName, throwOnMissingValue: false);
        }
    }

    private static void SetStartupLinux(bool enable)
    {
        var autostartDir = Path.Combine(
            Environment.GetEnvironmentVariable("XDG_CONFIG_HOME")
                ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config"),
            "autostart");

        Directory.CreateDirectory(autostartDir);
        var desktopFile = Path.Combine(autostartDir, "getMediaPlayerInfo.desktop");

        if (enable)
        {
            var exe = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? string.Empty;
            File.WriteAllText(desktopFile, $"""
                [Desktop Entry]
                Type=Application
                Name=getMediaPlayerInfo
                Exec={exe} --minimized
                Hidden=false
                NoDisplay=false
                X-GNOME-Autostart-enabled=true
                """);
        }
        else if (File.Exists(desktopFile))
        {
            File.Delete(desktopFile);
        }
    }

    private static void SetStartupMacOs(bool enable)
    {
        var launchAgentsDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            "Library", "LaunchAgents");

        Directory.CreateDirectory(launchAgentsDir);
        var plistFile = Path.Combine(launchAgentsDir, "com.getmediaplayerinfo.app.plist");

        if (enable)
        {
            var exe = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? string.Empty;
            File.WriteAllText(plistFile, $"""
                <?xml version="1.0" encoding="UTF-8"?>
                <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
                <plist version="1.0">
                <dict>
                    <key>Label</key>
                    <string>com.getmediaplayerinfo.app</string>
                    <key>ProgramArguments</key>
                    <array>
                        <string>{exe}</string>
                        <string>--minimized</string>
                    </array>
                    <key>RunAtLoad</key>
                    <true/>
                </dict>
                </plist>
                """);
        }
        else if (File.Exists(plistFile))
        {
            File.Delete(plistFile);
        }
    }
}
