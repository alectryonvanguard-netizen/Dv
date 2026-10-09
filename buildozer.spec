[app]
title = Sam Ng
package.name = samng
package.domain = org.samng
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,gif,bmp,kv,atlas,txt
version = 0.4
requirements = python3,kivy,plyer
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png

# If your final app uses additional Python packages, add them to requirements.
# Keep Android permissions only for features your app actually uses.

[buildozer]
log_level = 2
warn_on_root = 1
