using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DesktopApp.Models;
using DesktopApp.Services;

namespace DesktopApp.ViewModels;

/// <summary>
/// ViewModel for the Settings tab.
/// Edits a live copy of <see cref="AppConfig"/> and persists it on save.
/// </summary>
public partial class SettingsViewModel : ViewModelBase
{
    private readonly ConfigService _configService;
    private AppConfig _config;

    // -----------------------------------------------------------------------
    // Observable connection list
    // -----------------------------------------------------------------------

    [ObservableProperty] private ObservableCollection<ServerConnection> _connections = [];
    [ObservableProperty] private ServerConnection? _selectedConnection;
    [ObservableProperty] private int _activeConnectionIndex = 0;

    // -----------------------------------------------------------------------
    // Observable scalar settings
    // -----------------------------------------------------------------------

    [ObservableProperty] private int _pollingIntervalMs = 2000;
    [ObservableProperty] private bool _useWebSocket = true;
    [ObservableProperty] private bool _notificationsEnabled = true;
    [ObservableProperty] private string _selectedTheme = "Default";
    [ObservableProperty] private bool _minimizeToTray = true;
    [ObservableProperty] private bool _startMinimized = false;
    [ObservableProperty] private bool _discordPresenceEnabled = false;
    [ObservableProperty] private bool _registerStartup = false;

    // Edit fields for the selected connection
    [ObservableProperty] private string _editName = string.Empty;
    [ObservableProperty] private string _editHost = "localhost";
    [ObservableProperty] private int _editPort = 8765;

    [ObservableProperty] private string _saveStatus = string.Empty;

    public IReadOnlyList<string> ThemeOptions { get; } = ["Default", "Light", "Dark"];

    // -----------------------------------------------------------------------
    // Constructor
    // -----------------------------------------------------------------------

    public SettingsViewModel(ConfigService configService)
    {
        _configService = configService;
        _config = _configService.Load();
        LoadFromConfig(_config);
    }

    private void LoadFromConfig(AppConfig cfg)
    {
        Connections = new ObservableCollection<ServerConnection>(cfg.Connections);
        ActiveConnectionIndex = Math.Max(0, Math.Min(cfg.ActiveConnectionIndex, cfg.Connections.Count - 1));
        SelectedConnection = Connections.ElementAtOrDefault(ActiveConnectionIndex);

        PollingIntervalMs       = cfg.PollingIntervalMs;
        UseWebSocket            = cfg.UseWebSocket;
        NotificationsEnabled    = cfg.NotificationsEnabled;
        SelectedTheme           = cfg.Theme;
        MinimizeToTray          = cfg.MinimizeToTray;
        StartMinimized          = cfg.StartMinimized;
        DiscordPresenceEnabled  = cfg.DiscordPresenceEnabled;
        RegisterStartup         = cfg.RegisterStartup;

        if (SelectedConnection is not null)
            PopulateEditFields(SelectedConnection);
    }

    partial void OnSelectedConnectionChanged(ServerConnection? value)
    {
        if (value is not null)
            PopulateEditFields(value);
    }

    private void PopulateEditFields(ServerConnection c)
    {
        EditName = c.Name;
        EditHost = c.Host;
        EditPort = c.Port;
    }

    // -----------------------------------------------------------------------
    // Commands
    // -----------------------------------------------------------------------

    [RelayCommand]
    private void ApplyConnection()
    {
        if (SelectedConnection is null)
            return;

        var idx = Connections.IndexOf(SelectedConnection);
        if (idx < 0)
            return;

        var updated = SelectedConnection with
        {
            Name = EditName.Trim(),
            Host = EditHost.Trim(),
            Port = EditPort,
        };

        Connections[idx] = updated;
        SelectedConnection = updated;
    }

    [RelayCommand]
    private void AddConnection()
    {
        var conn = new ServerConnection
        {
            Name = $"Server {Connections.Count + 1}",
            Host = "localhost",
            Port = 8765,
        };
        Connections.Add(conn);
        SelectedConnection = conn;
    }

    [RelayCommand]
    private void RemoveConnection()
    {
        if (SelectedConnection is null || Connections.Count <= 1)
            return;

        Connections.Remove(SelectedConnection);
        SelectedConnection = Connections.FirstOrDefault();
    }

    [RelayCommand]
    private void Save()
    {
        // Apply any pending edit
        ApplyConnection();

        _config.Connections           = Connections.ToList();
        var selectedIdx = SelectedConnection is not null
            ? Connections.IndexOf(SelectedConnection)
            : -1;
        _config.ActiveConnectionIndex = selectedIdx >= 0 ? selectedIdx : 0;
        _config.PollingIntervalMs     = PollingIntervalMs;
        _config.UseWebSocket          = UseWebSocket;
        _config.NotificationsEnabled  = NotificationsEnabled;
        _config.Theme                 = SelectedTheme;
        _config.MinimizeToTray        = MinimizeToTray;
        _config.StartMinimized        = StartMinimized;
        _config.DiscordPresenceEnabled = DiscordPresenceEnabled;
        _config.RegisterStartup       = RegisterStartup;

        _configService.Save(_config);

        // Apply startup registration
        TrayIconService.SetStartupRegistration(RegisterStartup);

        SaveStatus = "✔ Settings saved";
        _ = ClearSaveStatusAsync();
    }

    private async Task ClearSaveStatusAsync()
    {
        await Task.Delay(2000);
        SaveStatus = string.Empty;
    }

    /// <summary>Return the currently active connection based on the saved index.</summary>
    public ServerConnection GetActiveConnection() =>
        Connections.ElementAtOrDefault(ActiveConnectionIndex) ?? Connections[0];

    /// <summary>Reload config from disk (e.g. after external change).</summary>
    public void Reload()
    {
        _config = _configService.Load();
        LoadFromConfig(_config);
    }
}
