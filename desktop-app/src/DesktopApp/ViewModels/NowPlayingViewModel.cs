using System.Collections.ObjectModel;
using System.Timers;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DesktopApp.Models;
using DesktopApp.Services;
using Timer = System.Timers.Timer;

namespace DesktopApp.ViewModels;

/// <summary>
/// ViewModel for the Now Playing tab.
/// Drives the media card, progress bar, recent history strip, and connection panel.
/// </summary>
public partial class NowPlayingViewModel : ViewModelBase
{
    private readonly HistoryViewModel _historyVm;
    private readonly TrayIconService _trayService;
    private readonly NotificationService _notificationService;
    private readonly Timer _progressTimer;

    // -----------------------------------------------------------------------
    // Observable properties
    // -----------------------------------------------------------------------

    [ObservableProperty] private string _title = "No media playing";
    [ObservableProperty] private string _artist = string.Empty;
    [ObservableProperty] private string _album = string.Empty;
    [ObservableProperty] private string _sourceApp = string.Empty;
    [ObservableProperty] private string _statusLabel = "UNKNOWN";
    [ObservableProperty] private string _statusColor = "#888888";
    [ObservableProperty] private double _progress = 0.0;
    [ObservableProperty] private string _positionText = "--:--";
    [ObservableProperty] private string _durationText = "--:--";
    [ObservableProperty] private bool _isCached = false;
    [ObservableProperty] private string _connectionStatus = "Disconnected";
    [ObservableProperty] private string _connectionColor = "#CC3333";
    [ObservableProperty] private string _serverInfo = string.Empty;
    [ObservableProperty] private bool _hasMedia = false;
    [ObservableProperty] private string _clipboardButtonText = "📋 Copy";

    // Interpolated position for smooth progress (ms)
    private long _positionMs;
    private long _durationMs;
    private DateTime _lastUpdateTime;
    private bool _isPlaying;
    private MediaInfo? _currentMedia;

    // -----------------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------------

    public NowPlayingViewModel(
        HistoryViewModel historyVm,
        TrayIconService trayService,
        NotificationService notificationService)
    {
        _historyVm = historyVm;
        _trayService = trayService;
        _notificationService = notificationService;

        _progressTimer = new Timer(500) { AutoReset = true };
        _progressTimer.Elapsed += OnProgressTick;
        _progressTimer.Start();
    }

    // -----------------------------------------------------------------------
    // Public API called by MainWindowViewModel
    // -----------------------------------------------------------------------

    public void OnMediaUpdated(MediaInfo? media, SystemInfo? system, bool cached, string connectionName)
    {
        Dispatcher.UIThread.Post(() =>
        {
            IsCached = cached;

            // Update server info
            if (system is not null)
                ServerInfo = $"{system.Hostname}  ({system.Platform})";

            if (media is null || string.IsNullOrWhiteSpace(media.Title))
            {
                HasMedia = false;
                Title = "No media playing";
                Artist = string.Empty;
                Album = string.Empty;
                SourceApp = string.Empty;
                StatusLabel = "UNKNOWN";
                StatusColor = "#888888";
                _isPlaying = false;
                _positionMs = 0;
                _durationMs = 0;
                Progress = 0;
                PositionText = "--:--";
                DurationText = "--:--";
                _trayService.UpdateMedia(null);
                return;
            }

            HasMedia = true;

            // Detect track change for history & notification
            bool trackChanged = _currentMedia is null
                || _currentMedia.Title != media.Title
                || _currentMedia.Artist != media.Artist;

            _currentMedia = media;

            Title = media.Title;
            Artist = media.Artist;
            Album = media.Album;
            SourceApp = media.SourceApp;

            (StatusLabel, StatusColor) = media.Status switch
            {
                PlaybackStatus.Playing => ("▶ PLAYING",  "#22BB55"),
                PlaybackStatus.Paused  => ("⏸ PAUSED",   "#EEAA33"),
                PlaybackStatus.Stopped => ("⏹ STOPPED",  "#888888"),
                PlaybackStatus.Cached  => ("💾 CACHED",  "#5599FF"),
                _                      => ("● UNKNOWN",  "#888888"),
            };

            // Update progress tracking
            _positionMs      = media.PositionMs ?? 0;
            _durationMs      = media.DurationMs ?? 0;
            _lastUpdateTime  = DateTime.UtcNow;
            _isPlaying       = media.IsPlaying;

            UpdateProgressDisplay();

            // History + notification on track change
            if (trackChanged && !string.IsNullOrWhiteSpace(media.Title))
            {
                _historyVm.AddEntry(HistoryEntry.FromMedia(media, connectionName));
                _notificationService.Show(
                    media.Title,
                    string.IsNullOrWhiteSpace(media.Artist) ? media.SourceApp : media.Artist);
            }

            _trayService.UpdateMedia(media);
        });
    }

    public void OnConnectionStateChanged(ConnectionState state, string? error)
    {
        Dispatcher.UIThread.Post(() =>
        {
            (ConnectionStatus, ConnectionColor) = state switch
            {
                ConnectionState.Connecting    => ("⏳ Connecting…", "#EEAA33"),
                ConnectionState.Connected     => ("🔗 Connected",    "#22BB55"),
                ConnectionState.Error         => ($"⚠ Error: {error ?? "unknown"}", "#CC3333"),
                ConnectionState.Disconnected  => ("⬤ Disconnected", "#CC3333"),
                _                             => ("⬤ Disconnected", "#888888"),
            };
        });
    }

    // -----------------------------------------------------------------------
    // Commands
    // -----------------------------------------------------------------------

    [RelayCommand]
    private async Task CopyToClipboard()
    {
        if (_currentMedia is null) return;

        var text = string.IsNullOrWhiteSpace(_currentMedia.Artist)
            ? _currentMedia.Title
            : $"{_currentMedia.Title} — {_currentMedia.Artist}";

        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime { MainWindow: { } win })
        {
            var clipboard = TopLevel.GetTopLevel(win)?.Clipboard;
            if (clipboard is not null)
            {
                await clipboard.SetTextAsync(text);
                ClipboardButtonText = "✔ Copied!";
                await Task.Delay(1500);
                ClipboardButtonText = "📋 Copy";
            }
        }
    }

    // -----------------------------------------------------------------------
    // Progress interpolation
    // -----------------------------------------------------------------------

    private void OnProgressTick(object? sender, ElapsedEventArgs e)
    {
        if (!_isPlaying || _durationMs <= 0)
            return;

        var elapsed = (DateTime.UtcNow - _lastUpdateTime).TotalMilliseconds;
        _positionMs += (long)elapsed;
        _lastUpdateTime = DateTime.UtcNow;

        if (_positionMs > _durationMs)
            _positionMs = _durationMs;

        Dispatcher.UIThread.Post(UpdateProgressDisplay);
    }

    private void UpdateProgressDisplay()
    {
        if (_durationMs > 0)
        {
            Progress = Math.Clamp((double)_positionMs / _durationMs, 0.0, 1.0);
            PositionText = MediaInfo.FormatMs(_positionMs);
            DurationText = MediaInfo.FormatMs(_durationMs);
        }
        else if (_positionMs > 0)
        {
            Progress = 0;
            PositionText = MediaInfo.FormatMs(_positionMs);
            DurationText = "--:--";
        }
        else
        {
            Progress = 0;
            PositionText = "--:--";
            DurationText = "--:--";
        }
    }

    public void Dispose()
    {
        _progressTimer.Dispose();
    }
}
