using System.IO;
using DesktopApp.Models;
using DesktopApp.Services;
using Xunit;

namespace DesktopApp.Tests.Services;

public class ConfigServiceTests : IDisposable
{
    private readonly string _tmpPath;
    private readonly ConfigService _sut;

    public ConfigServiceTests()
    {
        _tmpPath = Path.Combine(Path.GetTempPath(), $"gmp_test_{Guid.NewGuid()}.json");
        _sut = new ConfigService(_tmpPath);
    }

    public void Dispose()
    {
        if (File.Exists(_tmpPath))
            File.Delete(_tmpPath);
    }

    [Fact]
    public void Load_WhenFileDoesNotExist_ReturnsDefaultConfig()
    {
        var config = _sut.Load();

        Assert.NotNull(config);
        Assert.Single(config.Connections);
        Assert.Equal("localhost", config.Connections[0].Host);
        Assert.Equal(8765, config.Connections[0].Port);
    }

    [Fact]
    public void SaveAndLoad_RoundTrips_AllProperties()
    {
        var original = new AppConfig
        {
            Connections =
            [
                new ServerConnection { Name = "Work PC", Host = "192.168.1.10", Port = 9000 },
                new ServerConnection { Name = "Home",    Host = "10.0.0.5",     Port = 8765 },
            ],
            ActiveConnectionIndex = 1,
            PollingIntervalMs     = 3000,
            UseWebSocket          = false,
            NotificationsEnabled  = false,
            Theme                 = "Dark",
            MinimizeToTray        = false,
            StartMinimized        = true,
            DiscordPresenceEnabled = true,
            RegisterStartup       = false,
        };

        _sut.Save(original);
        var loaded = _sut.Load();

        Assert.Equal(2, loaded.Connections.Count);
        Assert.Equal("Work PC",      loaded.Connections[0].Name);
        Assert.Equal("192.168.1.10", loaded.Connections[0].Host);
        Assert.Equal(9000,           loaded.Connections[0].Port);
        Assert.Equal(1,              loaded.ActiveConnectionIndex);
        Assert.Equal(3000,           loaded.PollingIntervalMs);
        Assert.False(loaded.UseWebSocket);
        Assert.False(loaded.NotificationsEnabled);
        Assert.Equal("Dark",         loaded.Theme);
        Assert.False(loaded.MinimizeToTray);
        Assert.True(loaded.StartMinimized);
        Assert.True(loaded.DiscordPresenceEnabled);
    }

    [Fact]
    public void Load_WhenFileIsCorrupted_ReturnsDefaultConfig()
    {
        File.WriteAllText(_tmpPath, "not valid json {{{{");
        var config = _sut.Load();

        Assert.NotNull(config);
        Assert.Single(config.Connections);
    }

    [Fact]
    public void Save_CreatesParentDirectoryIfMissing()
    {
        var nested = Path.Combine(Path.GetTempPath(),
            $"gmp_nested_{Guid.NewGuid()}", "sub", "config.json");
        var svc = new ConfigService(nested);
        svc.Save(new AppConfig());

        Assert.True(File.Exists(nested));
        File.Delete(nested);
        Directory.Delete(Path.GetDirectoryName(Path.GetDirectoryName(nested)!)!, recursive: true);
    }
}
