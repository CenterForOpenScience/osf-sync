## Setting up a development system

The following things must be installed in order to work with the development version of the program,
and to create packaged, installable executables for distribution to others.

In general, the version requirements are stricter on Windows than on Mac OS, due to the difficulty of
compiling binaries on Windows.

### Mac OS-specific instructions

- Install python 3.5.2:
    ```
    brew update ; brew doctor
    brew install python3
    ```

- Create a virtual env (based on python3!!), and activate said virtualenv
  `mkvirtualenv osf-sync -p \`which python 3\``

- Install requirements
  `pip install -r requirements.txt`

- If everything works, you will be able to run the GUI tool from the repo using:
  `inv start`

- After you log in, you will need to click the OSF icon in the system tray and select folders to sync under "Preferences".

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
  `pyinstaller deploy/OSF-Sync-windows.spec --clean`

On Mac OS:
  `pyinstaller deploy/OSF-Sync-mac.spec --clean`

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

Drag the bundled `OSF-Sync.app` into the disk image on the left side. Using finder, create an alias
to `Macintosh HD/Applications`, and drag the alias into the disk image on the right side.

When done, close the window. Return to disk utility and right-click on the image. Unmount and click eject partition.

Then click the disk image file. Choose "convert" to create a compressed, uneditable image for distribution.

# To sign the Mac version
    `codesign --verbose --force --deep --sign "Certificate Name" "OSF Sync.app"`
