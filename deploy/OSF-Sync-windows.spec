# -*- mode: python -*-

block_cipher = None

a = Analysis(['../start.py'],
             pathex=['D:\\Users\\cosadmin\\Documents\\GitHub\\OSF-Sync'],
             binaries=[
                ('/Users/cosadmin/AppData/Local/Programs/Python/Python35-32/Lib/site-packages/PyQt5/Qt/bin/Qt5Core.dll', ''),
                ('/Users/cosadmin/AppData/Local/Programs/Python/Python35-32/Lib/site-packages/PyQt5/Qt/bin/Qt5Gui.dll', ''),
                ('/Users/cosadmin/AppData/Local/Programs/Python/Python35-32/Lib/site-packages/PyQt5/Qt/bin/Qt5Svg.dll', ''),
                ('/Users/cosadmin/AppData/Local/Programs/Python/Python35-32/Lib/site-packages/PyQt5/Qt/bin/Qt5PrintSupport.dll', ''),
                ('/Users/cosadmin/AppData/Local/Programs/Python/Python35-32/Lib/site-packages/PyQt5/Qt/bin/Qt5Widgets.dll', ''),
             ],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          name='OSF Sync',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='deploy\\images\\cos_logo.ico')
