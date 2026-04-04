using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DesktopApp.Models;
using DesktopApp.Services;

namespace DesktopApp.ViewModels;

/// <summary>
/// Root ViewModel.
/// Orchestrates tab navigation, the API client lifecycle, and tray interaction.
/// </summary>
public partial class MainWindowViewModel : ViewModelBase, IAsyncDisposable
{
    private readonly ConfigService _configService;
    private readonly TrayIconService _trayService;
    private readonly NotificationService _notificationService;

    private ApiClient? _apiClient;
    private AppConfig _config;

    // -----------------------------------------------------------------------
    // Child ViewModels
    // -----------------------------------------------------------------------

    public NowPlayingViewModel NowPlaying { get; }
    public HistoryViewModel    History    { get; }
    public SettingsViewModel   Settings   { get; }

    // -----------------------------------------------------------------------
    // Observable properties
    // -----------------------------------------------------------------------

    [ObservableProperty] private int _selectedTabIndex = 0;
    [ObservableProperty] private string _windowTitle = "getMediaPlayerInfo";
    [ObservableProperty] private string _trayTooltip = "getMediaPlayerInfo";

    // -----------------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------------

    public MainWindowViewModel()
        : this(new ConfigService(), new TrayIconService(), new NotificationService()) { }

    public MainWindowViewModel(
        ConfigService configService,
        TrayIconService trayService,
        NotificationService notificationService)
    {
        _configService       = configService;
        _trayService         = trayService;
        _notificationService = notificationService;

        _config   = _configService.Load();
        History   = new HistoryViewModel();
        Settings  = new SettingsViewModel(_configService);
        NowPlaying = new NowPlayingViewModel(History, _trayService, _notificationService);

        // Propagate config options to services
        _notificationService.Enabled = _config.NotificationsEnabled;

        // Tray tooltip
        _trayService.TooltipChanged += (_, text) =>
            Dispatcher.UIThread.Post(() => TrayTooltip = text);

        // Watch for settings saves and reconnect if needed
        Settings.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(SettingsViewModel.SaveStatus) &&
                Settings.SaveStatus.StartsWith("✔"))
            {
                ReloadConfig();
            }
        };

        // Connect on startup
        Connect();
    }

    // -----------------------------------------------------------------------
    // Commands
    // -----------------------------------------------------------------------

    [RelayCommand]
    private void ShowWindow()
    {
        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime { MainWindow: { } win })
        {
            win.Show();
            win.WindowState = Avalonia.Controls.WindowState.Normal;
            win.Activate();
        }
    }

    [RelayCommand]
    private void ExitApp()
    {
        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime lifetime)
            lifetime.Shutdown();
    }

    [RelayCommand]
    private void NavigateToSettings() => SelectedTabIndex = 2;

    // -----------------------------------------------------------------------
    // Connection management
    // -----------------------------------------------------------------------

    private void Connect()
    {
        var connection = Settings.GetActiveConnection();

        _apiClient?.DisposeAsync();
        _apiClient = new ApiClient(
            connection,
            _config.PollingIntervalMs,
            _config.UseWebSocket);

        _apiClient.MediaUpdated += (_, e) =>
            NowPlaying.OnMediaUpdated(e.Media, e.System, e.Cached, connection.Name);

        _apiClient.ConnectionStateChanged += (_, e) =>
        {
            NowPlaying.OnConnectionStateChanged(e.State, e.Error);
            Dispatcher.UIThread.Post(() =>
                WindowTitle = e.State == ConnectionState.Connected
                    ? $"getMediaPlayerInfo — {connection.Name}"
                    : "getMediaPlayerInfo");
        };

        _apiClient.Start();
    }

    private void ReloadConfig()
    {
        _config = _configService.Load();
        _notificationService.Enabled = _config.NotificationsEnabled;
        Settings.Reload();

        // Restart client with new settings
        _ = RestartClientAsync();
    }

    private async Task RestartClientAsync()
    {
        if (_apiClient is not null)
            await _apiClient.StopAsync();

        Connect();
    }

    // -----------------------------------------------------------------------
    // IAsyncDisposable
    // -----------------------------------------------------------------------

    public async ValueTask DisposeAsync()
    {
        if (_apiClient is not null)
            await _apiClient.DisposeAsync();

        NowPlaying.Dispose();
    }
}
