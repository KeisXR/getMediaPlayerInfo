using DesktopApp.Models;
using DesktopApp.Services;
using Xunit;

namespace DesktopApp.Tests.Services;

public class ApiClientTests
{
    // -----------------------------------------------------------------------
    // ServerConnection URL helpers
    // -----------------------------------------------------------------------

    [Fact]
    public void ServerConnection_BaseUrl_FormatsCorrectly()
    {
        var conn = new ServerConnection { Host = "192.168.1.5", Port = 9000 };
        Assert.Equal("http://192.168.1.5:9000", conn.BaseUrl);
    }

    [Fact]
    public void ServerConnection_WsUrl_FormatsCorrectly()
    {
        var conn = new ServerConnection { Host = "myserver", Port = 8765 };
        Assert.Equal("ws://myserver:8765/ws", conn.WsUrl);
    }

    [Fact]
    public void ServerConnection_NowPlayingUrl_FormatsCorrectly()
    {
        var conn = new ServerConnection { Host = "localhost", Port = 8765 };
        Assert.Equal("http://localhost:8765/now-playing", conn.NowPlayingUrl);
    }

    [Fact]
    public void ServerConnection_ToString_IncludesNameAndAddress()
    {
        var conn = new ServerConnection { Name = "My PC", Host = "10.0.0.1", Port = 8765 };
        Assert.Contains("My PC",    conn.ToString());
        Assert.Contains("10.0.0.1", conn.ToString());
        Assert.Contains("8765",     conn.ToString());
    }

    // -----------------------------------------------------------------------
    // ApiClient state transitions
    // -----------------------------------------------------------------------

    [Fact]
    public async Task ApiClient_InitialState_IsDisconnected()
    {
        var conn = new ServerConnection();
        await using var client = new ApiClient(conn);

        Assert.Equal(ConnectionState.Disconnected, client.State);
    }

    [Fact]
    public async Task ApiClient_Stop_WithoutStart_DoesNotThrow()
    {
        var conn = new ServerConnection();
        await using var client = new ApiClient(conn);
        await client.StopAsync(); // should be a no-op
    }
}
