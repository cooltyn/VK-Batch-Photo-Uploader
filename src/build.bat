pyinstaller upload.py --onefile --clean --icon=icon.ico --windowed --distpath=../ --add-data=icon.ico;/
rmdir /s /q build
del upload.spec
