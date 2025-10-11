# Leaf

A place to store all of the things I need for Java modding to be publicly available.
This repository so far contains creation and storage of version manifests which are parsed from Steam manifest data, and also file hash tables so you can check if an install is valid.

# Generate them yourself!

1. Download the Steam manifests using [DepotDownloader](https://github.com/SteamRE/DepotDownloader) and pass the depots folder it generates to the generator.
2. Execute the generator! It takes a couple args, the required ones being `--depots-dir "path/to/depots` and `--output-dir "path/to/output"`. There is also a `--force` parameter for overwriting existing manifests, though you don't need to use that generally.
   Example: `leaf-generator --output-dir "C:\github\leaf" --depots-dir "G:\Steam\depots"`.

# Contributing

If you want to contribute in any way to the function of the leaf toolchain as a whole, you might want to take a look at the issues on the respective repositories, or use the project board I've set up [here](https://github.com/users/aoqia194/projects/6/views/1),
