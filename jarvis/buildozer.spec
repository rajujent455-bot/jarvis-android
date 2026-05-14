[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ico
version = 1.0

# Proven working: kivy==2.1.0 + cython==0.29.19 + p4a==2023.09.16
requirements = python3,kivy==2.1.0,requests,pypdf

orientation = portrait
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,RECORD_AUDIO
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
