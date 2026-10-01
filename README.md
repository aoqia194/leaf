<div align="center">

<h1>
    The data repository for
    <a href="https://pzwiki.net/wiki/Leaf">
        <img src="https://github.com/LeafPZ.png" width="24px" alt="LeafPZ Icon">
        leaf
    </a>
</h1>

![License](https://img.shields.io/github/license/LeafPZ/leaf?label=License)
![Python version](https://img.shields.io/badge/Python-3.14.0-blue?logo=python)
![Test status](https://github.com/LeafPZ/leaf/actions/workflows/test.yml/badge.svg?branch=main&label=test)
![Code Size](https://img.shields.io/github/languages/code-size/LeafPZ/leaf?label=Code%20Size)
![Maven status](https://img.shields.io/website?url=https%3A%2F%2Fmaven.aoqia.dev%2F&label=Maven)

</div>

A place to store all of the things I need for Java modding to be publicly available.
This repository so far contains creation and storage of version manifests which are parsed from Steam manifest data, and also file hash tables so you can check if an install is valid.

The generator is written in Python. It used to be in Rust for maximum speed, but the verbosity meant it took a really long time just to add some small things. Python, albeit slower than Rust, is more universal, and can be quite fast as well if optimised well. Getting rid of regex parsing entirely for basic string ops has basically made Python the same speed if not faster than Rust, while also doing a LOT more out of the gate such as downloading game files from Steam, decompiling the game, extracting files, etc.

# Generate them yourself!

> [!WARNING]
> You may be temporarily rate-limited by Steam if you decide to mass-generate depots. Be warned!

Setting up the generator requires [uv](https://docs.astral.sh/uv/getting-started/installation/). Also requires [DepotDownloader](https://github.com/steamre/depotdownloader) to be installed and on your path.

Running `uv sync` in the repository root will set up the Python virtual env and install all project dependencies through uv.
You may have to manually source the venv yourself if your shell doesn't automatically do it.
For example (using Fish shell):

```sh
source .venv/bin/activate.fish
```

Once the venv is active, you can simply run the generator by running some of the hatch build scripts:

```sh
hatch run generate --overwrite
```

Overwrite flag here means that it will delete all previously-generated files.

The buildscripts are just there to imitate how buildscripts are done in Node land, since UV doesn't have anything similar.
You can see all of the hatch buildscripts and what they do in the [pyproject.toml](./pyproject.toml)

# Outputs

After running the generator, it will cache downloaded content from Steam in `out/.cache`. These files will be reused if the generator is run again. All generated content for public viewing (such as index manifests and build manifests) will be in `dist/indexes` and `dist/manifests` respectively. `dist/loader` is reserved for [leaf-loader](https://github.com/LeafPZ/leaf-loader) manifests and are only used by [leaf-installer](https://github.com/LeafPZ/leaf-installer).

# Contributing

If you want to contribute in any way to the function of the leaf toolchain as a whole, you might want to take a look at the issues on the respective repositories.
