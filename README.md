# Leaf

A place to store all of the things I need for Java modding to be publicly available.
This repository so far contains creation and storage of version manifests which are parsed from Steam manifest data, and also file hash tables so you can check if an install is valid.

# Generate Them Yourself!

To generate the manifests yourself like I do, download the Steam manifests via [DepotDownloader](https://github.com/SteamRE/DepotDownloader) and pass the absolute path to the depots folder as an arg.
Example args for the program look like this: `-Dleaf.rootPath=C:\github\leaf -Dleaf.depotsPath=C:\Users\aoqia\depots`.
