# getMediaPlayerInfo — Desktop App

Cross-platform desktop client for [getMediaPlayerInfo](../README.md) built with **.NET 9** and **Avalonia UI 11**.

Connects to a running `getMediaPlayerInfo` Python server via **WebSocket** (real-time) or **HTTP polling** fallback, and displays the currently playing media in a native GUI on Windows, Linux, and macOS.

---

## Features

| Feature | Details |
|---|---|
| 🎵 Now Playing card | Title, artist, album, playback status, smooth progress bar |
| 📋 Play history | Timestamped log with search, CSV/JSON export |
| 🔗 Multi-server | Register multiple servers, switch between them |
| 🔔 OS notifications | Desktop notification on each track change |
| 🖥 System tray | Icon with current track tooltip, hide-to-tray support |
| 📋 Clipboard | One-click copy of "Title — Artist" |
| ⚙ Settings | Transport, theme (Light/Dark/System), startup registration |
| 🚀 Startup | Auto-launch at login (Windows registry / Linux .desktop / macOS LaunchAgent) |

---

## Getting Started

### Prerequisites

- [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9)
- A running `getMediaPlayerInfo` Python server (default: `localhost:8765`)

### Run (development)

```bash
cd desktop-app
dotnet run --project src/DesktopApp
```

### Build a self-contained executable

```bash
# Windows
dotnet publish src/DesktopApp -c Release -r win-x64 --self-contained -o out/windows

# Linux
dotnet publish src/DesktopApp -c Release -r linux-x64 --self-contained -o out/linux

# macOS (Intel)
dotnet publish src/DesktopApp -c Release -r osx-x64 --self-contained -o out/macos
```

### Run tests

```bash
dotnet test src/DesktopApp.Tests
```

---

## Project Structure

```
desktop-app/
├── DesktopApp.sln
└── src/
    ├── DesktopApp/
    │   ├── Program.cs              # Entry point
    │   ├── App.axaml / App.axaml.cs
    │   ├── Assets/                 # icon.ico
    │   ├── Models/
    │   │   ├── MediaInfo.cs        # Media data + PlaybackStatus enum
    │   │   ├── ApiResponse.cs      # API response models (HTTP + WebSocket)
    │   │   ├── AppConfig.cs        # AppConfig + ServerConnection
    │   │   └── HistoryEntry.cs     # Play history entry
    │   ├── Services/
    │   │   ├── ApiClient.cs        # WebSocket + HTTP polling client
    │   │   ├── ConfigService.cs    # JSON config (OS-appropriate dir)
    │   │   ├── NotificationService.cs  # Cross-platform OS notifications
    │   │   └── TrayIconService.cs  # Tray tooltip + startup registration
    │   └── ViewModels/
    │       ├── MainWindowViewModel.cs   # Root VM: navigation + client lifecycle
    │       ├── NowPlayingViewModel.cs   # Media card + progress interpolation
    │       ├── HistoryViewModel.cs      # History log + export
    │       └── SettingsViewModel.cs     # Config editing
    └── DesktopApp.Tests/
        ├── Services/
        │   ├── ApiClientTests.cs
        │   └── ConfigServiceTests.cs
        └── ViewModels/
            ├── MediaInfoTests.cs
            └── HistoryViewModelTests.cs
```

---

## Configuration

Configuration is stored as JSON in the OS-appropriate location:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\getMediaPlayerInfo\config.json` |
| Linux | `~/.config/getMediaPlayerInfo/config.json` |
| macOS | `~/Library/Application Support/getMediaPlayerInfo/config.json` |

---

## Connection Modes

| Mode | Description |
|---|---|
| WebSocket *(default)* | Connects to `ws://host:port/ws`; receives `media_update` messages in real-time |
| HTTP Polling | Falls back to polling `GET /now-playing` at the configured interval |

The client auto-reconnects with exponential back-off (up to 30 s) on any connection error.

---

## Tech Stack

| Component | Technology |
|---|---|
| UI Framework | [Avalonia UI 11.2](https://avaloniaui.net/) |
| MVVM | [CommunityToolkit.Mvvm 8.3](https://learn.microsoft.com/dotnet/communitytoolkit/mvvm/) |
| HTTP / WebSocket | `System.Net.Http.HttpClient` / `System.Net.WebSockets.ClientWebSocket` |
| JSON | `System.Text.Json` |
| Tests | xUnit 2.9 + Moq 4.20 |
| Target | `net9.0` (Windows / Linux / macOS) |
