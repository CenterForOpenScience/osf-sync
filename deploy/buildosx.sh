rm -f "./dist/OSF Sync Installer.dmg"; pyinstaller ./deploy/OSF-Sync-mac.spec --clean && appdmg "./deploy/dmg-build.json" "./dist/OSF Sync Installer.dmg"
