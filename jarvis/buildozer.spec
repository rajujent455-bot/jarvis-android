[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ico
version = 1.0

# FIX 1: Kivy version update kiya
requirements = python3,kivy==2.3.0

orientation = portrait
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24

# FIX 2: NDK 28c → 25b
android.ndk = 25b

android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
