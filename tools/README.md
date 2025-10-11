# Scripts

Here are just some useful things I use to create the manifests, but these are separate and are not required.



## depotdownloader_runner.py

This is a Python script that takes in the path to a txt file (see below for example of contents) and runs depotdownloader on all of the things.

###### Requirements

- depotdownloader ran on system at least once with the `--remember-password` parameter

- Steam account username used with depotdownloader in the environment variable `DEPOTDOWNLOADER_USERNAME`

###### Usage

`python depotdownloader_runner.py "list.txt" "C:\path\to\destination"`

###### Input file example

```rust
108600:108602:5996245470838825718:unstable
108600:108603:6529967175871940863
108600:108604:8495676860137747126
380870:380871:2175640781972158944
380870:380872:2859243753354680810
380870:380873:5956598524508335611
380870:380874:4651566147400075697
```

#### regex.txt

This is just a small regex snippet that pairs with depotdownloader_runner. You can copy paste some of the entries in the manifest table from [SteamDB](https://steamdb.info/depot/108603/manifests) into any notepad with regex replace.


