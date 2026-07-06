[app]
title = Фитнес Дневник
package.name = fitnessdiary
package.domain = org.fitness
source.dir = .
source.include_exts = py
version = 1.0

# Фиксируем стабильный Python 3.11 и hostpython3, под которые есть все библиотеки
requirements = python3==3.11.1,hostpython3==3.11.1,kivy,flask,sqlite3,jinja2,werkzeug,click,itsdangerous,setuptools,pyjnius

orientation = portrait
fullscreen = 1
android.permissions = INTERNET,WAKE_LOCK
android.api = 34
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a
android.private_storage = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
