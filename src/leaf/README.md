# Generator

Here lies a useful Python project I use to create the manifests.

#### Requirements

- DepotDownloader ran on system at least once with the `--remember-password` parameter
- Steam account username used with DepotDownloader in the environment variable `DEPOTDOWNLOADER_USERNAME`

#### Usage

```sh
hatch run generate --overwrite
```

#### Manifests.txt file example

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
