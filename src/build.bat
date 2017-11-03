pyinstaller upload.py --onefile --clean --icon=icon.ico --distpath=../
rmdir /s /q build
del upload.spec
