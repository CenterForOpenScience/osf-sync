Type   | Remote    | Local     | Resolution
:----: | :-------: | :-------: | :-----------------------------:
File   | Create    | Create    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Create    | Update    | N/A
File   | Create    | Delete    | N/A
File   | Create    | Move Src  | N/A
File   | Create    | Move Dest | N/A
File   | Update    | Create    | N/A
File   | Update    | Update    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Update    | Delete    | Download File
File   | Update    | Move Src  | Perform Move as Copy then Download File (Can't Detect)
File   | Update    | Move Dest | N/A
File   | Delete    | Create    | N/A
File   | Delete    | Update    | Upload as New
File   | Delete    | Delete    | Delete from DB
File   | Delete    | Move Src  | Move -> Create (Can't Detect)
File   | Delete    | Move Dest | Upload as New (Can't Detect)
File   | Move Src  | Create    | N/A
File   | Move Src  | Update    | Move then Upload as New
File   | Move Src  | Delete    | Ignore Delete (Can't Detect)
File   | Move Src  | Move Src  | Ignore Local Move (Can't Detect)
File   | Move Src  | Move Dest | Can't Detect
File   | Move Dest | Create    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Move Dest | Update    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Move Dest | Delete    | Download
File   | Move Dest | Move Src  | Upload Local as New (Can't Detect)
File   | Move Dest | Move Dest | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash( Can't Detect)
Folder | Create    | Create    | Create DB Entry
Folder | Create    | Update    | N/A
Folder | Create    | Delete    | N/A
Folder | Create    | Move Src  | N/A
Folder | Create    | Move Dest | Create DB Entry
Folder | Update    | Create    | N/A
Folder | Update    | Update    | Ignore
Folder | Update    | Delete    | Download Folder
Folder | Update    | Move Src  | Can't Detect
Folder | Update    | Move Dest | Can't Detect
Folder | Delete    | Create    | N/A
Folder | Delete    | Update    | Prompt User Theirs/Mine/Merge
Folder | Delete    | Delete    | Delete DB Entry
Folder | Delete    | Move Src  | Can't Detect
Folder | Delete    | Move Dest | Can't Detect
Folder | Move Src  | Create    | Create Folder
Folder | Move Src  | Update    | Upload as New (Recreate Directory) Move locally
Folder | Move Src  | Delete    | Ignore Delete
Folder | Move Src  | Move Src  | Can't Detect
Folder | Move Src  | Move Dest | Can't Detect
Folder | Move Dest | Create    | Create DB Entry
Folder | Move Dest | Update    | Prompt User Merge, resolve all file conflicts or rename
Folder | Move Dest | Delete    | Ignore Delete
Folder | Move Dest | Move Src  | Can't Detect
Folder | Move Dest | Move Dest | Can't Detect




Type   | Remote    | Local     | Resolution
:----: | :-------: | :-------: | :-----------------------------:
File   | Create    | Create    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Update    | Update    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Move Dest | Create    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Move Dest | Update    | Prompt User &#124;&#124; Rename &#124;&#124; Match Hash
File   | Delete    | Update    | Upload as New
File   | Delete    | Delete    | Delete DB Entry
File   | Move Src  | Update    | Move then Upload as New
File   | Move Dest | Delete    | Download File
File   | Update    | Delete    | Download File
Folder | Move Src  | Create    | Create Folder
Folder | Create    | Create    | Create DB Entry
Folder | Move Dest | Create    | Create DB Entry
Folder | Delete    | Delete    | Delete DB Entry
Folder | Update    | Delete    | Download Folder
Folder | Move Src  | Update    | Upload as New (Recreate Directory) Move locally
Folder | Delete    | Update    | Prompt User Theirs/Mine/Merge
Folder | Move Dest | Update    | Prompt User Merge, resolve all file conflicts or rename
Folder | Update    | Update    | Ignore
Folder | Move Dest | Delete    | Ignore Delete
Folder | Move Src  | Delete    | Ignore Delete
