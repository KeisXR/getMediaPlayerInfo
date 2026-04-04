namespace DesktopApp.Models;

/// <summary>
/// A single entry in the playback history log.
/// </summary>
public record HistoryEntry
{
    public DateTime Timestamp { get; init; } = DateTime.Now;
    public string Title { get; init; } = string.Empty;
    public string Artist { get; init; } = string.Empty;
    public string Album { get; init; } = string.Empty;
    public string SourceApp { get; init; } = string.Empty;
    public long? DurationMs { get; init; }
    public string ConnectionName { get; init; } = string.Empty;

    public string TimestampDisplay => Timestamp.ToString("yyyy-MM-dd HH:mm:ss");

    public string DurationDisplay => DurationMs.HasValue
        ? MediaInfo.FormatMs(DurationMs.Value)
        : "-";

    public static HistoryEntry FromMedia(MediaInfo media, string connectionName) =>
        new()
        {
            Timestamp     = DateTime.Now,
            Title         = media.Title,
            Artist        = media.Artist,
            Album         = media.Album,
            SourceApp     = media.SourceApp,
            DurationMs    = media.DurationMs,
            ConnectionName = connectionName,
        };
}
