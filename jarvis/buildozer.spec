[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# ── FIX 2: font file ko APK mein bundle karo ──────────────────────────────
source.include_patterns = assets/fonts/*.ttf

version = 1.1.0
requirements = python3,kivy==2.3.0,requests

orientation = portrait
fullscreen = 0

# ── Android settings ──────────────────────────────────────────────────────
android.api = 31
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a

# ── FIX 1: INTERNET permission zaroori hai API calls ke liye ─────────────
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
