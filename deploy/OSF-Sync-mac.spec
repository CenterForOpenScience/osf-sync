# -*- mode: python -*-

block_cipher = None


a = Analysis(['../start.py'],
             pathex=['/Users/michael/Projects/cos/osf-sync'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='OSF Sync',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='deploy/images/cos_logo.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='OSF Sync')
app = BUNDLE(coll,
             name='OSF Sync.app',
             icon='deploy/images/cos_logo.icns',
             bundle_identifier=None)
