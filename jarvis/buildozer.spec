[app]
title = JARVIS
package.name = jarvis
package.domain = org.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ico
version = 1.0
requirements = python3,kivy==2.3.0,anthropic,pypdf,reportlab,pillow,certifi,charset-normalizer,urllib3,idna,requests

orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.3.0

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, RECORD_AUDIO
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a

android.allow_backup = True
android.wakelock = False

[buildozer]
log_level = 2
warn_on_root = 1
