using System.Text.Json.Serialization;

namespace DesktopApp.Models;

/// <summary>
/// System information returned by the API.
/// </summary>
public record SystemInfo
{
    [JsonPropertyName("os")]
    public string Os { get; init; } = string.Empty;

    [JsonPropertyName("hostname")]
    public string Hostname { get; init; } = string.Empty;

    [JsonPropertyName("platform")]
    public string Platform { get; init; } = string.Empty;
}

/// <summary>
/// Full response from /now-playing endpoint.
/// </summary>
public record ApiResponse
{
    [JsonPropertyName("system")]
    public SystemInfo? System { get; init; }

    [JsonPropertyName("media")]
    public MediaInfo? Media { get; init; }

    [JsonPropertyName("last_updated")]
    public string LastUpdated { get; init; } = string.Empty;

    [JsonPropertyName("cached")]
    public bool Cached { get; init; }

    [JsonPropertyName("error")]
    public string? Error { get; init; }
}

/// <summary>
/// Response from the root / endpoint.
/// </summary>
public record StatusResponse
{
    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("service")]
    public string Service { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public string Version { get; init; } = string.Empty;

    [JsonPropertyName("system")]
    public SystemInfo? System { get; init; }

    [JsonPropertyName("provider")]
    public string? Provider { get; init; }

    [JsonPropertyName("cache_ttl_seconds")]
    public int CacheTtlSeconds { get; init; } = 30;
}

/// <summary>
/// WebSocket message from /ws endpoint.
/// </summary>
public record WsMessage
{
    [JsonPropertyName("type")]
    public string Type { get; init; } = string.Empty;

    [JsonPropertyName("system")]
    public SystemInfo? System { get; init; }

    [JsonPropertyName("media")]
    public MediaInfo? Media { get; init; }

    [JsonPropertyName("last_updated")]
    public string LastUpdated { get; init; } = string.Empty;

    [JsonPropertyName("cached")]
    public bool Cached { get; init; }
}
