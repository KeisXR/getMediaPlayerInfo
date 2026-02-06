# Media Player API - Android Standalone

Pythonなしで動作する軽量シェルスクリプト版。

## 必要環境

- Root権限 (KernelSU / Magisk)
- busybox または toybox（多くのカスタムROMに含まれる）

## インストール

```bash
# PCからAndroidにファイルを転送
adb push android-standalone /sdcard/media-api

# Androidでインストール
adb shell
su
cd /sdcard/media-api
sh install.sh
```

## 使い方

### 手動起動

```bash
su -c '/data/local/tmp/media-api/start.sh'
```

### 停止

```bash
su -c '/data/local/tmp/media-api/stop.sh'
```

### 直接実行

```bash
su -c 'sh /sdcard/media-api/media-api.sh 8765'
```

## API

| Endpoint | 説明 |
|----------|------|
| `GET /` | ステータス確認 |
| `GET /now-playing` | 現在の再生情報 |

※ WebSocketは非対応（シェルスクリプトでは複雑すぎるため）

## ファイル構成

- `media-api.sh` - メインスクリプト（nc使用）
- `media-api-socat.sh` - socat版（より安定）
- `install.sh` - インストールスクリプト
