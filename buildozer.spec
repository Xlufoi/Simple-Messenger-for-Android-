[app]
title = SocketChat
package.name = socketchat
package.domain = org.artem.socketchat

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET

# 32-bit (armeabi-v7a) и 64-bit (arm64-v8a) в одном APK
android.archs = arm64-v8a, armeabi-v7a

android.api = 33
android.minapi = 21
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
