# Media Player API

マルチプラットフォーム対応のメディア再生情報取得API

## 対応プラットフォーム

| Platform | 取得方法 | 備考 |
|----------|---------|------|
| Windows | SMTC | Windows 10以降 |
| macOS | Now Playing (MediaRemote.framework) | macOS 10.14以降 |
| Linux | MPRIS (D-Bus) / WayDroid (Shell) | D-Bus対応プレイヤー / WayDroidコンテナ内のアプリ |
| Android (App) | MediaSession API | android-app-v2 |

## 起動方法

### Windows
```powershell
.\run.bat
```

### Linux
```bash
chmod +x run.sh
./run.sh
```

#### WayDroid 設定 (オプション)

WayDroid内のメディア情報を取得するには、以下の設定を行ってください：

1. `waydroid shell` コマンドをパスワードなしで実行できるように設定
   ```bash
   echo 'username ALL=(ALL) NOPASSWD: /usr/bin/waydroid shell *' | sudo tee /etc/sudoers.d/waydroid
   sudo chmod 440 /etc/sudoers.d/waydroid
   ```
   ※ `username` はあなたのユーザー名に置き換えてください。

### macOS
```bash
pip install -r requirements.txt
python main.py
```

macOS では `MediaRemote.framework`（プライベートAPI）を使用して、システムの Now Playing セッションから情報を取得します。追加のインストールは不要です。

### Android (アプリ版) 
1. [Releases](../../releases) から APK をダウンロード
2. インストールして起動
3. 「Grant Permission」→ 通知アクセス権限を許可
4. 「Start Server」をタップ
5. `http://<端末IP>:8765/now-playing` でアクセス
6. WebSocket: `ws://<端末IP>:8766` でリアルタイム更新を受信可能

※ GitHub Actionsでビルド: `android-app-v2/` ディレクトリ参照

## Discord Rich Presence 連携

再生中のメディアをDiscordのアクティビティに表示できます。

### 準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、**Client ID** を取得してください。
2. PCでDiscordアプリを起動しておきます。

### 設定方法

Client ID は以下のいずれかで設定できます（上から優先）：

1. **コマンドライン引数**（毎回指定）
2. **`config.json`** – 作業ディレクトリに作成
   ```json
   { "DISCORD_CLIENT_ID": "123456789012345678" }
   ```
3. **`.env`** – 作業ディレクトリに作成
   ```
   DISCORD_CLIENT_ID=123456789012345678
   ```

### 実行

```bash
# config.json / .env で設定済みの場合
python discord_presence.py

# または引数で直接指定
python discord_presence.py --client-id <YOUR_CLIENT_ID>
```

停止するには `Ctrl+C` を押してください。

## API

- `GET /` - ステータス確認
- `GET /now-playing` - 現在の再生情報取得
- `GET /vrchat/now-playing` - VRChat内の再生情報取得（Windows/Linux Proton対応）
- `WebSocket /ws` - リアルタイム更新

FastAPI の自動ドキュメントは `http://localhost:8765/docs` で確認できます。

## VRChat (Linux/Proton)

Linux で Steam/Proton 経由の VRChat を使用している場合、ログファイルは自動的に以下のパスを検索します：

```
~/.local/share/Steam/steamapps/compatdata/438100/pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/
```

カスタムの Steam ライブラリパスは `STEAM_LIBRARY` 環境変数で指定できます：

```bash
STEAM_LIBRARY=/mnt/games python main.py
```

## テスト

```bash
pip install -r requirements-dev.txt
pytest tests/
```

