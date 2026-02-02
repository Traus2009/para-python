[app]
title = Mi POS Venta
package.name = posventa
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xlsx
version = 0.1
requirements = python3,kivy==2.3.0,kivymd,pandas,openpyxl,fpdf,pyzbar,plyer,opencv4android

orientation = portrait
fullscreen = 0
android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
