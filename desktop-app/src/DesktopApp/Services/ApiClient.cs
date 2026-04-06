using System.Net.Http;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using DesktopApp.Models;

namespace DesktopApp.Services;

/// <summary>
/// Connection state of the API client.
/// </summary>
public enum ConnectionState
{
    Disconnected,
    Connecting,
    Connected,
    Error,
}

/// <summary>
/// Event args for media update events.
/// </summary>
public class MediaUpdatedEventArgs(MediaInfo? media, SystemInfo? system, bool cached) : EventArgs
{
    public MediaInfo? Media { get; } = media;
    public SystemInfo? System { get; } = system;
    public bool Cached { get; } = cached;
}

/// <summary>
/// Event args for connection state changes.
/// </summary>
public class ConnectionStateChangedEventArgs(ConnectionState state, string? error = null) : EventArgs
{
    public ConnectionState State { get; } = state;
    public string? Error { get; } = error;
}

/// <summary>
/// Connects to a getMediaPlayerInfo server via WebSocket (preferred) or HTTP polling fallback.
/// Raises <see cref="MediaUpdated"/> whenever the playing media changes.
/// </summary>
public sealed class ApiClient : IAsyncDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly HttpClient _http;
    private ClientWebSocket? _ws;
    private CancellationTokenSource? _cts;
    private Task? _runTask;
    private ServerConnection _connection;
    private int _pollingIntervalMs;
    private bool _useWebSocket;

    public event EventHandler<MediaUpdatedEventArgs>? MediaUpdated;
    public event EventHandler<ConnectionStateChangedEventArgs>? ConnectionStateChanged;
    public event EventHandler<string>? DebugLog;

    public ConnectionState State { get; private set; } = ConnectionState.Disconnected;

    public ApiClient(ServerConnection connection, int pollingIntervalMs = 2000, bool useWebSocket = true)
    {
        _connection = connection;
        _pollingIntervalMs = pollingIntervalMs;
        _useWebSocket = useWebSocket;
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
    }

    /// <summary>Update the target server without restarting if already running.</summary>
    public void UpdateConnection(ServerConnection connection, int pollingIntervalMs, bool useWebSocket)
    {
        _connection = connection;
        _pollingIntervalMs = pollingIntervalMs;
        _useWebSocket = useWebSocket;
    }

    /// <summary>Start connecting and streaming media updates.</summary>
    public void Start()
    {
        if (_runTask is { IsCompleted: false })
            return;

        LogDebug($"Starting ApiClient. Mode={(_useWebSocket ? "WebSocket" : "Polling")} Endpoint={_connection.BaseUrl}");
        _cts = new CancellationTokenSource();
        _runTask = RunAsync(_cts.Token);
    }

    /// <summary>Stop all background activity.</summary>
    public async Task StopAsync()
    {
        if (_cts is null)
            return;

        LogDebug("Stopping ApiClient.");
        await _cts.CancelAsync();
        if (_runTask is not null)
        {
            try { await _runTask.ConfigureAwait(false); }
            catch (OperationCanceledException) { }
        }

        _cts.Dispose();
        _cts = null;
        _runTask = null;
        SetState(ConnectionState.Disconnected);
    }

    private async Task RunAsync(CancellationToken ct)
    {
        var backoffMs = 1000;

        while (!ct.IsCancellationRequested)
        {
            try
            {
                if (_useWebSocket)
                {
                    try
                    {
                        await RunWebSocketAsync(ct).ConfigureAwait(false);
                    }
                    catch (OperationCanceledException)
                    {
                        throw;
                    }
                    catch (Exception wsEx)
                    {
                        LogDebug($"WebSocket failed: {wsEx.Message}");
                        LogDebug("Falling back to HTTP polling mode.");
                        await RunPollingAsync(ct).ConfigureAwait(false);
                    }
                }
                else
                {
                    await RunPollingAsync(ct).ConfigureAwait(false);
                }

                backoffMs = 1000;
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                LogDebug($"Run loop error: {ex.Message}. Retrying in {backoffMs}ms.");
                SetState(ConnectionState.Error, ex.Message);
                await Task.Delay(backoffMs, ct).ConfigureAwait(false);
                backoffMs = Math.Min(backoffMs * 2, 30_000);
            }
        }

        LogDebug("ApiClient stopped.");
        SetState(ConnectionState.Disconnected);
    }

    // -----------------------------------------------------------------------
    // WebSocket mode
    // -----------------------------------------------------------------------

    private async Task RunWebSocketAsync(CancellationToken ct)
    {
        SetState(ConnectionState.Connecting);
        LogDebug($"Connecting WebSocket: {_connection.WsUrl}");

        _ws?.Dispose();
        _ws = new ClientWebSocket();

        await _ws.ConnectAsync(new Uri(_connection.WsUrl), ct).ConfigureAwait(false);
        LogDebug("WebSocket connected.");
        SetState(ConnectionState.Connected);

        var buffer = new byte[64 * 1024];

        while (_ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
        {
            var result = await _ws.ReceiveAsync(buffer, ct).ConfigureAwait(false);

            if (result.MessageType == WebSocketMessageType.Close)
            {
                await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, ct).ConfigureAwait(false);
                break;
            }

            if (result.MessageType != WebSocketMessageType.Text)
                continue;

            var json = Encoding.UTF8.GetString(buffer, 0, result.Count);

            // Handle multi-frame messages
            while (!result.EndOfMessage)
            {
                result = await _ws.ReceiveAsync(buffer, ct).ConfigureAwait(false);
                json += Encoding.UTF8.GetString(buffer, 0, result.Count);
            }

            // Respond to pings
            if (json.Trim() == "ping")
            {
                var pong = Encoding.UTF8.GetBytes("pong");
                await _ws.SendAsync(pong, WebSocketMessageType.Text, true, ct).ConfigureAwait(false);
                continue;
            }

            var msg = JsonSerializer.Deserialize<WsMessage>(json, JsonOptions);
            if (msg?.Type is "connected" or "media_update")
            {
                LogDebug($"WebSocket message: {msg.Type} media={(msg.Media is null ? "null" : msg.Media.Title)}");
                RaiseMediaUpdated(msg.Media, msg.System, msg.Cached);
            }
        }
    }

    // -----------------------------------------------------------------------
    // HTTP polling mode
    // -----------------------------------------------------------------------

    private async Task RunPollingAsync(CancellationToken ct)
    {
        SetState(ConnectionState.Connecting);
        LogDebug($"Starting HTTP polling: {_connection.NowPlayingUrl} every {_pollingIntervalMs}ms");

        // Verify reachability first
        var initial = await FetchNowPlayingAsync(ct).ConfigureAwait(false);
        SetState(ConnectionState.Connected);
        if (initial is not null)
            RaiseMediaUpdated(initial.Media, initial.System, initial.Cached);

        while (!ct.IsCancellationRequested)
        {
            try
            {
                var resp = await FetchNowPlayingAsync(ct).ConfigureAwait(false);
                if (resp is not null)
                {
                    LogDebug($"HTTP media update: {(resp.Media is null ? "null" : resp.Media.Title)}");
                    RaiseMediaUpdated(resp.Media, resp.System, resp.Cached);
                }
            }
            catch (HttpRequestException ex)
            {
                LogDebug($"HTTP polling error: {ex.Message}");
                SetState(ConnectionState.Error, ex.Message);
                throw;
            }

            await Task.Delay(_pollingIntervalMs, ct).ConfigureAwait(false);
        }
    }

    private async Task<ApiResponse?> FetchNowPlayingAsync(CancellationToken ct)
    {
        using var response = await _http.GetAsync(_connection.NowPlayingUrl, ct).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync(ct).ConfigureAwait(false);

        if (!response.IsSuccessStatusCode)
        {
            var snippet = body.Length > 200 ? body[..200] + "..." : body;
            throw new HttpRequestException(
                $"HTTP {(int)response.StatusCode} {response.ReasonPhrase}. Body: {snippet}");
        }

        var parsed = JsonSerializer.Deserialize<ApiResponse>(body, JsonOptions);
        if (parsed is null)
            throw new HttpRequestException("Failed to deserialize /now-playing response.");

        return parsed;
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    private void RaiseMediaUpdated(MediaInfo? media, SystemInfo? system, bool cached) =>
        MediaUpdated?.Invoke(this, new MediaUpdatedEventArgs(media, system, cached));

    private void SetState(ConnectionState state, string? error = null)
    {
        if (State == state && error is null)
            return;
        State = state;
        LogDebug(error is null
            ? $"Connection state: {state}"
            : $"Connection state: {state} ({error})");
        ConnectionStateChanged?.Invoke(this, new ConnectionStateChangedEventArgs(state, error));
    }

    private void LogDebug(string message) =>
        DebugLog?.Invoke(this, $"[{DateTime.Now:HH:mm:ss}] {message}");

    public async ValueTask DisposeAsync()
    {
        await StopAsync().ConfigureAwait(false);
        _http.Dispose();
        _ws?.Dispose();
    }
}
