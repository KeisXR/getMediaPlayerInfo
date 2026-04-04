using System.Text.Json.Serialization;

namespace DesktopApp.Models;

/// <summary>
/// Playback status enum matching the Python API values.
/// </summary>
public enum PlaybackStatus
{
    Playing,
    Paused,
    Stopped,
    Unknown,
    Cached,
}

/// <summary>
/// Media information matching the Python API response format.
/// </summary>
public record MediaInfo
{
    [JsonPropertyName("source_app")]
    public string SourceApp { get; init; } = string.Empty;

    [JsonPropertyName("title")]
    public string Title { get; init; } = string.Empty;

    [JsonPropertyName("artist")]
    public string Artist { get; init; } = string.Empty;

    [JsonPropertyName("album")]
    public string Album { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string StatusRaw { get; init; } = "unknown";

    [JsonPropertyName("position_ms")]
    public long? PositionMs { get; init; }

    [JsonPropertyName("duration_ms")]
    public long? DurationMs { get; init; }

    [JsonPropertyName("thumbnail")]
    public string? Thumbnail { get; init; }

    [JsonIgnore]
    public PlaybackStatus Status => StatusRaw switch
    {
        "playing" => PlaybackStatus.Playing,
        "paused"  => PlaybackStatus.Paused,
        "stopped" => PlaybackStatus.Stopped,
        "cached"  => PlaybackStatus.Cached,
        _         => PlaybackStatus.Unknown,
    };

    [JsonIgnore]
    public bool IsPlaying => Status == PlaybackStatus.Playing;

    [JsonIgnore]
    public bool HasProgress => PositionMs.HasValue && DurationMs.HasValue && DurationMs.Value > 0;

    [JsonIgnore]
    public double ProgressFraction =>
        HasProgress ? (double)PositionMs!.Value / DurationMs!.Value : 0.0;

    public static string FormatMs(long ms)
    {
        var totalSeconds = ms / 1000;
        var minutes = totalSeconds / 60;
        var seconds = totalSeconds % 60;
        return $"{minutes}:{seconds:D2}";
    }
}
