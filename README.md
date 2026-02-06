# Media Player API

マルチプラットフォーム対応のメディア再生情報取得API

## 対応プラットフォーム

| Platform | 取得方法 | 備考 |
|----------|---------|------|
| Windows | SMTC | Windows 10以降 |
| Linux | MPRIS (D-Bus) / WayDroid (Shell) | D-Bus対応プレイヤー / WayDroidコンテナ内のアプリ |
| Android (App) | NotificationListener | 実装不備により動作しません |
| Android (Shell) | dumpsys | 実装不備により動作しません |

ただし、Windows / Linuxでしか動作しません。

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


### Android (アプリ版) 
1. [Releases](../../releases) から APK をダウンロード
2. インストールして起動
3. 「Grant Permission」→ 通知アクセス権限を許可
4. 「Start Server」をタップ
5. `http://<端末IP>:8765/now-playing` でアクセス

※ GitHub Actionsでビルド: `android-app/` ディレクトリ参照

### Android (Termux + Python)
```bash
# ファイルを転送してインストール
adb push android-standalone /sdcard/media-api
adb shell su -c 'sh /sdcard/media-api/install.sh'

# 起動
adb shell su -c '/data/local/tmp/media-api/start.sh'
```

## Discord Rich Presence 連携

再生中のメディアをDiscordのアクティビティに表示できます。

### 準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成し、**Client ID** を取得してください。
2. PCでDiscordアプリを起動しておきます。

### 実行

```bash
# 仮想環境を使用する場合 (推奨)
./venv/bin/python discord_presence.py --client-id <YOUR_CLIENT_ID>

# または
python discord_presence.py --client-id <YOUR_CLIENT_ID>
```

停止するには `Ctrl+C` を押してください。

## API

- `GET /` - ステータス確認
- `GET /now-playing` - 現在の再生情報取得
- `WebSocket /ws` - リアルタイム更新（Python版のみ）


