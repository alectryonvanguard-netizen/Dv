SAM NG APK PROJECT

This ZIP contains your existing Python/Kivy app as main.py, plus the starter
Buildozer configuration and icon.

MAIN FILE
- main.py: the Sam Ng app code you supplied
- buildozer.spec: Android APK build configuration
- icon.png: app icon
- .github/workflows/build-apk.yml: optional GitHub Actions build workflow

IMPORTANT
- This is the project ZIP, not a compiled APK.
- The app currently stores posts in memory while it is running. Posts, likes,
  saves and comments are not permanently saved and are not uploaded online.
- Online accounts, messaging, server publishing, and system sharing are not
  implemented in this prototype.
- The Android build must still be tested. Video playback depends on Android
  codecs, and the media picker should be tested on the target phone.
- Keep a safe copy of this ZIP. For updates, preserve the same package ID and
  signing key, and increase the version code when making release builds.
