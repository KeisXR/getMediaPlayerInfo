# Media Player API

マルチプラットフォーム対応のメディア再生情報取得API

## 対応プラットフォーム

| Platform | 取得方法 | 備考 |
|----------|---------|------|
| Windows | SMTC | Windows 10以降 |
| Linux | MPRIS (D-Bus) | D-Bus対応プレイヤー |
| Android (App) | NotificationListener | **Root不要** ⭐ |
| Android (Shell) | dumpsys | Root必要 (KernelSU/Magisk) |

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

### Android (アプリ版) ⭐ Root不要
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

## API

- `GET /` - ステータス確認
- `GET /now-playing` - 現在の再生情報取得
- `WebSocket /ws` - リアルタイム更新（Python版のみ）
