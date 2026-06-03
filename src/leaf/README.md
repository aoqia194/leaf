# Generator

Here are just some useful modules/scripts I use to create the manifests.
Most of these modules (like downloader, generator) can be run like a normal script with a main() function and will do things!

## downloader.py

Takes in the path to a txt file and runs DepotDownloader on all of the elements.

#### Requirements

- DepotDownloader ran on system at least once with the `--remember-password` parameter
- Steam account username used with DepotDownloader in the environment variable `DEPOTDOWNLOADER_USERNAME`

#### Usage

```sh
uv run python downloader.py --manifests-file manifests.txt --output-path "./manifests/{0}/" -filelist "files.txt"
uv run python downloader.py --manifests-file manifests.txt --output-path "./manifests/" -manifest-only
```

Note that the `{0}` is a predefined format argument that corresponds to the manifest id.

#### Input file example

You can prepare the input file by selecting the manifest table text from SteamDB and using regex:

```regex
.+?\s+–\s+\d\d:\d\d:\d\d\sUTC\s[\d\.]*\s*\w+\s\w+\s(\d+)\s(\S+).*$
```

Replace with: `<appid>:<depotid>:$1:$2`

Example file:

```rust
108600:108602:5996245470838825718:unstable
108600:108603:6529967175871940863:
108600:108604:8495676860137747126:
380870:380871:2175640781972158944:
380870:380872:2859243753354680810:
380870:380873:5956598524508335611:
380870:380874:4651566147400075697:
```
