"""
Internationalization support.
Supports Japanese (ja) and English (en).
"""
from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "ja": {
        # Navigation
        "nav_now_playing": "🎵 Now Playing",
        "nav_history": "📋 再生履歴",
        "nav_provider": "🖥 プロバイダ",
        "nav_api": "🌐 API サーバー",
        "nav_discord": "🎮 Discord",
        "nav_statistics": "📊 統計",
        "nav_settings": "⚙ 設定",
        # Common
        "app_name": "getMediaPlayerInfo Desktop",
        "status_running": "実行中",
        "status_stopped": "停止中",
        "status_connected": "接続済み",
        "status_disconnected": "未接続",
        "status_playing": "▶ 再生中",
        "status_paused": "⏸ 一時停止",
        "status_stopped_play": "⏹ 停止",
        "status_unknown": "不明",
        "btn_start": "起動",
        "btn_stop": "停止",
        "btn_refresh": "🔄 更新",
        "btn_copy": "📋 コピー",
        "btn_export_csv": "CSV エクスポート",
        "btn_export_json": "JSON エクスポート",
        "btn_clear": "🗑 クリア",
        "btn_open_browser": "ブラウザで開く",
        "btn_save": "保存",
        "btn_apply": "適用",
        # Now Playing
        "np_no_media": "再生中のメディアはありません",
        "np_source": "ソース",
        "np_copied": "クリップボードにコピーしました",
        "np_copy_template": "コピーのテンプレート",
        # History
        "hist_title": "再生履歴",
        "hist_col_time": "時刻",
        "hist_col_title": "タイトル",
        "hist_col_artist": "アーティスト",
        "hist_col_album": "アルバム",
        "hist_col_source": "ソース",
        "hist_col_duration": "再生時間",
        "hist_search_placeholder": "検索...",
        "hist_empty": "履歴がありません",
        "hist_clear_confirm": "履歴をすべて削除しますか？",
        "hist_export_success": "エクスポートしました",
        # Provider
        "prov_title": "メディアプロバイダ",
        "prov_active": "アクティブなプロバイダ",
        "prov_filter_mode": "フィルターモード",
        "prov_filter_all": "すべて (all)",
        "prov_filter_no_browser": "ブラウザ除外 (no-browser)",
        "prov_filter_apps_only": "アプリのみ (apps-only)",
        "prov_info": "プロバイダ情報",
        "prov_platform": "プラットフォーム",
        "prov_class": "プロバイダクラス",
        "prov_restart_required": "変更を適用するにはサーバーの再起動が必要です",
        # API Server
        "api_title": "API サーバー",
        "api_host": "ホスト",
        "api_port": "ポート",
        "api_url": "URL",
        "api_log": "アクセスログ",
        "api_log_clear": "ログをクリア",
        "api_qr_title": "モバイル接続 (QR コード)",
        "api_docs": "API ドキュメント (Swagger UI)",
        "api_start_success": "API サーバーを起動しました",
        "api_stop_success": "API サーバーを停止しました",
        "api_already_running": "サーバーはすでに起動しています",
        # Discord
        "discord_title": "Discord Rich Presence",
        "discord_enable": "Discord Rich Presence を有効にする",
        "discord_client_id": "Client ID",
        "discord_client_id_hint": "Discord Developer Portal で作成したアプリの Client ID",
        "discord_template": "表示テンプレート",
        "discord_template_hint": "使用可能: {title}, {artist}, {album}, {source}, {status}",
        "discord_preview": "プレビュー",
        "discord_connected": "Discord に接続しました",
        "discord_disconnected": "Discord から切断しました",
        "discord_not_found": "Discord が見つかりません（Discord デスクトップが起動しているか確認してください）",
        # Statistics
        "stats_title": "再生統計",
        "stats_today": "今日の再生時間",
        "stats_week": "今週の再生時間",
        "stats_total": "総再生時間",
        "stats_top_artists": "よく聴くアーティスト",
        "stats_top_sources": "使用プレーヤー",
        "stats_no_data": "データがありません",
        "stats_tracks_today": "今日の再生曲数",
        "stats_tracks_total": "総再生曲数",
        # Settings
        "set_title": "設定",
        "set_general": "一般",
        "set_theme": "テーマ",
        "set_theme_dark": "ダーク",
        "set_theme_light": "ライト",
        "set_theme_system": "システム",
        "set_language": "言語",
        "set_autostart": "Windows/Linux 起動時に自動スタート",
        "set_autostart_note": "Windows: レジストリに登録 / Linux: ~/.config/autostart に追加",
        "set_notifications": "曲変更時にデスクトップ通知を表示",
        "set_cache_ttl": "キャッシュ TTL (秒)",
        "set_clipboard_template": "クリップボードコピーのテンプレート",
        "set_webhook": "Webhook 設定",
        "set_webhook_url": "Webhook URL",
        "set_webhook_hint": "曲が変わると POST リクエストを送信します（空欄で無効）",
        "set_lastfm": "Last.fm スクロブル",
        "set_lastfm_api_key": "API Key",
        "set_lastfm_secret": "Shared Secret",
        "set_lastfm_username": "ユーザー名",
        "set_lastfm_session_key": "Session Key",
        "set_update_check": "アップデートを確認",
        "set_saved": "設定を保存しました",
        # Tray
        "tray_show": "ウィンドウを表示",
        "tray_hide": "ウィンドウを隠す",
        "tray_copy_now_playing": "Now Playing をコピー",
        "tray_quit": "終了",
        "tray_no_media": "再生なし",
        # Dialogs
        "dlg_confirm": "確認",
        "dlg_yes": "はい",
        "dlg_no": "いいえ",
        "dlg_ok": "OK",
        "dlg_cancel": "キャンセル",
        "dlg_error": "エラー",
        "dlg_info": "情報",
        "dlg_warning": "警告",
    },
    "en": {
        # Navigation
        "nav_now_playing": "🎵 Now Playing",
        "nav_history": "📋 History",
        "nav_provider": "🖥 Provider",
        "nav_api": "🌐 API Server",
        "nav_discord": "🎮 Discord",
        "nav_statistics": "📊 Statistics",
        "nav_settings": "⚙ Settings",
        # Common
        "app_name": "getMediaPlayerInfo Desktop",
        "status_running": "Running",
        "status_stopped": "Stopped",
        "status_connected": "Connected",
        "status_disconnected": "Disconnected",
        "status_playing": "▶ Playing",
        "status_paused": "⏸ Paused",
        "status_stopped_play": "⏹ Stopped",
        "status_unknown": "Unknown",
        "btn_start": "Start",
        "btn_stop": "Stop",
        "btn_refresh": "🔄 Refresh",
        "btn_copy": "📋 Copy",
        "btn_export_csv": "Export CSV",
        "btn_export_json": "Export JSON",
        "btn_clear": "🗑 Clear",
        "btn_open_browser": "Open in Browser",
        "btn_save": "Save",
        "btn_apply": "Apply",
        # Now Playing
        "np_no_media": "Nothing is playing",
        "np_source": "Source",
        "np_copied": "Copied to clipboard",
        "np_copy_template": "Copy template",
        # History
        "hist_title": "Play History",
        "hist_col_time": "Time",
        "hist_col_title": "Title",
        "hist_col_artist": "Artist",
        "hist_col_album": "Album",
        "hist_col_source": "Source",
        "hist_col_duration": "Duration",
        "hist_search_placeholder": "Search...",
        "hist_empty": "No history yet",
        "hist_clear_confirm": "Delete all history?",
        "hist_export_success": "Exported successfully",
        # Provider
        "prov_title": "Media Provider",
        "prov_active": "Active Provider",
        "prov_filter_mode": "Filter Mode",
        "prov_filter_all": "All (all)",
        "prov_filter_no_browser": "No Browser (no-browser)",
        "prov_filter_apps_only": "Apps Only (apps-only)",
        "prov_info": "Provider Info",
        "prov_platform": "Platform",
        "prov_class": "Provider Class",
        "prov_restart_required": "Server restart required to apply changes",
        # API Server
        "api_title": "API Server",
        "api_host": "Host",
        "api_port": "Port",
        "api_url": "URL",
        "api_log": "Access Log",
        "api_log_clear": "Clear Log",
        "api_qr_title": "Mobile Access (QR Code)",
        "api_docs": "API Docs (Swagger UI)",
        "api_start_success": "API server started",
        "api_stop_success": "API server stopped",
        "api_already_running": "Server is already running",
        # Discord
        "discord_title": "Discord Rich Presence",
        "discord_enable": "Enable Discord Rich Presence",
        "discord_client_id": "Client ID",
        "discord_client_id_hint": "Client ID from your Discord Developer Portal application",
        "discord_template": "Display Template",
        "discord_template_hint": "Available: {title}, {artist}, {album}, {source}, {status}",
        "discord_preview": "Preview",
        "discord_connected": "Connected to Discord",
        "discord_disconnected": "Disconnected from Discord",
        "discord_not_found": "Discord not found (make sure Discord desktop is running)",
        # Statistics
        "stats_title": "Statistics",
        "stats_today": "Today's Listening Time",
        "stats_week": "This Week",
        "stats_total": "Total Listening Time",
        "stats_top_artists": "Top Artists",
        "stats_top_sources": "Top Players",
        "stats_no_data": "No data available",
        "stats_tracks_today": "Tracks Today",
        "stats_tracks_total": "Total Tracks",
        # Settings
        "set_title": "Settings",
        "set_general": "General",
        "set_theme": "Theme",
        "set_theme_dark": "Dark",
        "set_theme_light": "Light",
        "set_theme_system": "System",
        "set_language": "Language",
        "set_autostart": "Launch at system startup",
        "set_autostart_note": "Windows: registry / Linux: ~/.config/autostart",
        "set_notifications": "Show desktop notification on track change",
        "set_cache_ttl": "Cache TTL (seconds)",
        "set_clipboard_template": "Clipboard copy template",
        "set_webhook": "Webhook",
        "set_webhook_url": "Webhook URL",
        "set_webhook_hint": "Sends a POST request when the track changes (leave empty to disable)",
        "set_lastfm": "Last.fm Scrobbling",
        "set_lastfm_api_key": "API Key",
        "set_lastfm_secret": "Shared Secret",
        "set_lastfm_username": "Username",
        "set_lastfm_session_key": "Session Key",
        "set_update_check": "Check for updates",
        "set_saved": "Settings saved",
        # Tray
        "tray_show": "Show Window",
        "tray_hide": "Hide Window",
        "tray_copy_now_playing": "Copy Now Playing",
        "tray_quit": "Quit",
        "tray_no_media": "Nothing playing",
        # Dialogs
        "dlg_confirm": "Confirm",
        "dlg_yes": "Yes",
        "dlg_no": "No",
        "dlg_ok": "OK",
        "dlg_cancel": "Cancel",
        "dlg_error": "Error",
        "dlg_info": "Info",
        "dlg_warning": "Warning",
    },
}

_current_lang: str = "ja"


def set_language(lang: str) -> None:
    """Set the active language (ja or en)."""
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def get_language() -> str:
    """Get the currently active language code."""
    return _current_lang


def tr(key: str) -> str:
    """Return the translated string for *key* in the current language.

    Falls back to English, then the key itself if not found.
    """
    lang_dict = TRANSLATIONS.get(_current_lang, {})
    if key in lang_dict:
        return lang_dict[key]
    # Fallback to English
    return TRANSLATIONS.get("en", {}).get(key, key)
