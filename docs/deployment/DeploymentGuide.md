## Setting up a development system

The following things must be installed in order to work with the development version of the program,
and to create packaged, installable executables for distribution to others.

In general, the version requirements are stricter on Windows than on Mac OS, due to the difficulty of
compiling binaries on Windows.

Separate MacOS setup instructions are available and will be added here at a later date.


- `Python` >= 3.4
  - The program will run on Python 3.5+, but [3.4.x](https://www.python.org/downloads/release/python-343/) is
  recommended for Windows operating systems, for best compatibility with precompiled Windows PyQT binaries.
  - On Windows, be sure to select a custom install, and choose the option to add Python (and script folders)
  to the system PATH automatically.
- `pip`
  - Should already come with python. Make sure it can be run via the command line.
- `git`
  - On Windows, the [GitHub desktop client](https://desktop.github.com/) provides a viable installation. (default
  data folder is `My Documents\GitHub`)
- [qt5.5](http://www.qt.io/download-open-source/)
  - Can de-select QT 5.4 from the installer to save disk space; only need 5.5. Other options left as-is.
- [pyqt5](https://riverbankcomputing.com/software/pyqt/download5)
    - Used PyQt5-5.5.1-gpl-Py3.4-Qt5.5.1-x32.exe (PyQT version should be built to match Python version, eg 3.4)

### Additional Windows requirements

- [InnoSetup](http://www.jrsoftware.org/isdl.php)
  - Tested with v5.5.6
- MS Visual Studio (Windows-only)
    - Not required to build and run the application, but some extensions (such as SQLAlchemy) offer better performance
    via C extensions.
    - Ideally use the same version of Visual Studio used to compiled your version of Python. The current build
    machine works with VS 2015.


## Preparing your build environment
Navigate to the cloned OSF offline source code directory and install all requirements. If you use a
virtual environment, make sure that PyQT is installed to that venv.
  - `pip install -r requirements.txt`

## Building for deployment
### Create the binary
On Windows:
  `pyinstaller --onedir --onefile --name=OSF-Offline --icon=deploy\\images\\cos_logo.ico --windowed start.py`

On Mac OS:
  `pyinstaller --onedir --onefile --name=OSF-Offline --icon=deploy/images/cos_logo.icns --windowed start.py`

After the first run, PyInstaller will create a .spec file that can be used for future builds on your machine.

### Create an installer
#### Windows
Open InnoSetup, and select the `osfoffline-setup.iss` script. In the editor, change all lines referencing `IEUser`
to point to your project directory.

Save the file. From the *Build* menu, select *Compile*. An installer will be deposited in the specified output folder.

#### Mac OS (.dmg file)
DMG files are created using *Disk Utility*, which comes bundled with Mac OS. Create a new DMG file each time to keep
the file size from growing too large; space may not be freed up when a file inside the image is overwritten/deleted.

Open disk utility and click the "new image" toolbar button. Choose a destination to save the file,
and an image name (different fields). Right-click on the image name in the Disk Utility sidebar,
and open the disk image (in finder).

To customize the DMG file, right-click inside the disk image and choose "show view options".
Select the following settings:
- Always open in icon view
- Icon size 128x128
- Background (drag picture to box): `OSF-Offline/deploy/images/OSF-Offline-background.png`

Drag the bundled `OSF-Offline.app` into the disk image on the left side. Using finder, create an alias
to `Macintosh HD/Applications`, and drag the alias into the disk image on the right side.

When done, close the window. Return to disk utility and right-click on the image. Unmount and click eject partition.

Then click the disk image file. Choose "convert" to create a compressed, uneditable image for distribution.

## Troubleshooting

PyInstaller needs to be modified with a fix for a windows bug. Version 3.0 (on PyPi) does not contain the fix, but
it is available in the PyInstaller github repo (development version); the bugfix version has been added to
`requirements.txt`. A symptom of this error is a message that "tuple object has no attribute 'replace'".

Sometimes pyinstaller will raise an exception due to problems importing `cy***.util`. If that happens,
it can be resolved by manually editing the PyInstaller source code to add an import statement in the location
indicated by the traceback.
