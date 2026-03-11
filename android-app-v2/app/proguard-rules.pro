# Add project specific ProGuard rules here.

# Keep Gson serialization models
-keepclassmembers class com.mediaplayerapi.model.** { *; }

# Keep NanoHTTPD
-keep class fi.iki.elonen.** { *; }
