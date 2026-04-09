using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using DesktopApp.Models;

namespace DesktopApp.Services;

/// <summary>
/// Loads and saves <see cref="AppConfig"/> to a JSON file in the OS-appropriate config directory.
/// </summary>
public class ConfigService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
    };

    private readonly string _configPath;

    public ConfigService()
    {
        var dir = GetConfigDirectory();
        Directory.CreateDirectory(dir);
        _configPath = Path.Combine(dir, "config.json");
    }

    /// <summary>Visible for testing.</summary>
    public ConfigService(string configPath)
    {
        _configPath = configPath;
        Directory.CreateDirectory(Path.GetDirectoryName(configPath)!);
    }

    public string ConfigPath => _configPath;

    public AppConfig Load()
    {
        if (!File.Exists(_configPath))
            return new AppConfig();

        try
        {
            var json = File.ReadAllText(_configPath);
            return JsonSerializer.Deserialize<AppConfig>(json, JsonOptions) ?? new AppConfig();
        }
        catch
        {
            return new AppConfig();
        }
    }

    public void Save(AppConfig config)
    {
        var json = JsonSerializer.Serialize(config, JsonOptions);
        File.WriteAllText(_configPath, json);
    }

    // -----------------------------------------------------------------------
    // Platform helpers
    // -----------------------------------------------------------------------

    private static string GetConfigDirectory()
    {
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            return Path.Combine(appData, "getMediaPlayerInfo");
        }

        if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
        {
            var home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return Path.Combine(home, "Library", "Application Support", "getMediaPlayerInfo");
        }

        // Linux / other Unix
        var xdgConfig = Environment.GetEnvironmentVariable("XDG_CONFIG_HOME");
        if (!string.IsNullOrWhiteSpace(xdgConfig))
            return Path.Combine(xdgConfig, "getMediaPlayerInfo");

        var homeDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return Path.Combine(homeDir, ".config", "getMediaPlayerInfo");
    }
}
