# -*- mode: python -*-

block_cipher = None


a = Analysis(['/Users/nchen/Projects/start.py'],
             pathex=['/Users/nchen/Projects/OSF-Offline'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='OSF-Sync',
          debug=False,
          strip=None,
          upx=True,
          console=False , icon='deploy/images/cos_logo.icns')
app = BUNDLE(exe,
             name='OSF-Sync.app',
             icon='deploy/images/cos_logo.icns',
             bundle_identifier=None)

