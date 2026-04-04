using DesktopApp.Models;
using Xunit;

namespace DesktopApp.Tests.ViewModels;

public class MediaInfoTests
{
    [Theory]
    [InlineData("playing", PlaybackStatus.Playing)]
    [InlineData("paused",  PlaybackStatus.Paused)]
    [InlineData("stopped", PlaybackStatus.Stopped)]
    [InlineData("cached",  PlaybackStatus.Cached)]
    [InlineData("unknown", PlaybackStatus.Unknown)]
    [InlineData("",        PlaybackStatus.Unknown)]
    public void Status_ParsedCorrectly(string raw, PlaybackStatus expected)
    {
        var info = new MediaInfo { StatusRaw = raw };
        Assert.Equal(expected, info.Status);
    }

    [Fact]
    public void IsPlaying_TrueOnlyWhenStatusIsPlaying()
    {
        Assert.True(new MediaInfo { StatusRaw = "playing" }.IsPlaying);
        Assert.False(new MediaInfo { StatusRaw = "paused"  }.IsPlaying);
        Assert.False(new MediaInfo { StatusRaw = "stopped" }.IsPlaying);
    }

    [Fact]
    public void HasProgress_TrueWhenBothPositionAndDurationPresent()
    {
        Assert.True(new MediaInfo { PositionMs = 1000, DurationMs = 5000 }.HasProgress);
        Assert.False(new MediaInfo { PositionMs = 1000                   }.HasProgress);
        Assert.False(new MediaInfo {                   DurationMs = 5000 }.HasProgress);
        Assert.False(new MediaInfo { PositionMs = 1000, DurationMs = 0   }.HasProgress);
    }

    [Fact]
    public void ProgressFraction_ComputedCorrectly()
    {
        var info = new MediaInfo { PositionMs = 2500, DurationMs = 5000 };
        Assert.Equal(0.5, info.ProgressFraction, precision: 5);
    }

    [Theory]
    [InlineData(0,      "0:00")]
    [InlineData(1000,   "0:01")]
    [InlineData(60000,  "1:00")]
    [InlineData(90000,  "1:30")]
    [InlineData(3661000, "61:01")]
    public void FormatMs_ReturnsExpectedString(long ms, string expected)
    {
        Assert.Equal(expected, MediaInfo.FormatMs(ms));
    }

    [Fact]
    public void HistoryEntry_FromMedia_MapsFieldsCorrectly()
    {
        var media = new MediaInfo
        {
            Title     = "My Song",
            Artist    = "Artist",
            Album     = "Album",
            SourceApp = "Spotify",
            DurationMs = 180_000,
        };

        var entry = HistoryEntry.FromMedia(media, "Local PC");

        Assert.Equal("My Song",  entry.Title);
        Assert.Equal("Artist",   entry.Artist);
        Assert.Equal("Album",    entry.Album);
        Assert.Equal("Spotify",  entry.SourceApp);
        Assert.Equal("Local PC", entry.ConnectionName);
        Assert.Equal("3:00",     entry.DurationDisplay);
    }

    [Fact]
    public void HistoryEntry_DurationDisplay_NullDuration_ReturnsDash()
    {
        var entry = new HistoryEntry { DurationMs = null };
        Assert.Equal("-", entry.DurationDisplay);
    }
}
