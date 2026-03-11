# Media Player API - Android App v2

Root不要で動作するAndroidアプリ版Media Player API。

## 旧版（android-app）からの改善点

- **MediaSession専用監視**: 通知（Notification）とMediaSessionの2重取得を廃止し、MediaSession APIのみで取得
- **Python版互換API**: フィールド名（`source_app`, `position_ms`, `duration_ms`）を統一
- **キャッシュ機構**: TTL 30秒のキャッシュを実装
- **Material Design UI**: XMLレイアウト + MaterialCardView + AppCompatActivity
- **Now Playing表示**: アプリ画面で再生中のメディア情報をリアルタイム表示
- **コード構造改善**: モデルクラス分離、ユーティリティ分離

## 機能

- **MediaSession API** で再生中のメディア情報を取得
- **HTTP API** (ポート8765) で情報を提供
- **Root不要** - 通知アクセス権限のみ必要

## APIエンドポイント

| Endpoint | 説明 |
|----------|------|
| `GET /` | ステータス確認 |
| `GET /now-playing` | 現在の再生情報 |

## ビルド方法

### GitHub Actions（推奨）

1. このリポジトリをGitHubにプッシュ
2. Actionsタブでビルド結果を確認
3. Artifactsから APK をダウンロード

### ローカルビルド

```bash
cd android-app-v2
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

## 使い方

1. APKをインストール
2. アプリを開いて「Grant Permission」をタップ
3. 設定画面で「Media Player API」を有効化
4. アプリに戻り「Start Server」をタップ
5. 音楽を再生して `http://<IP>:8765/now-playing` にアクセス

## 対応アプリ

MediaSessionを使用する全ての音楽アプリに対応:
- Spotify
- YouTube Music
- Amazon Music
- Apple Music
- その他多数

## 必要権限

- **通知アクセス権限** - MediaSessionアクセスに必要
- **インターネット** - ローカルHTTPサーバーの提供
