### Output structure

```yaml
# An example generated raw version manifest file that is internal to the generator.
# This file is the base of the pipeline. It has information related to the game classes/decompiled code, JAR manifest, and other important information.
- out/raw/1.2.3.json
# An example human-managed override file that is internal to the generator.
# This file has the ability to override anything in the previously-generated raw manifest file (see above).
- overrides/1.2.3.toml
# An example generated game version file that is public-facing.
# This version file has already gone through the inherits tree merge and override processing.
- dist/manifests/1.2.3.json
- dist/indexes/1.2.3.json
- dist/index.json
```

### Unique version identification

Some versions (usually pre-b42 unstable) may not have any truely-unique build information like a git hash or an internal revision number (used for a short period at the start of b42 unstable).

To solve this in a cross-platform way, I've devised a little format for hashing game and Steam metadata, hopefully this will be enough to create fully-unique version identifiers.

The hash will be a SHA-1 hash of these components, in this specific format:

```js
<major>.<minor>.<patch>:<steam_branch>-<manifest_date>
```
