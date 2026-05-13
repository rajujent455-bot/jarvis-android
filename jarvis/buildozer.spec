[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ico
version = 1.0
requirements = python3,kivy==2.3.0,pillow==10.1.0,urllib3,certifi,charset-normalizer,idna,requests

orientation = portrait

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True
android.release_artifact = apk

p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
