[app]

title = Mini RTS
package.name = minirts
package.domain = org.minirts

source.dir = .
source.include_exts = py,png,jpg,json,ttf
source.exclude_dirs = bin, .github, .buildozer, __pycache__
source.exclude_patterns = README.md

version = 6.0

requirements = python3,kivy==2.3.0

orientation = landscape
fullscreen = 1

# Réseau : nécessaire pour le multijoueur Wi-Fi
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1
