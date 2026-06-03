"""
A small wrapper script around DepotDownloader.
Calling the main function will parse the manifests.txt file.
"""

import os
from pathlib import Path
from typing import Optional

from loguru import logger

from leaf import util


def download(
    app_id: str,
    depot_id: str,
    manifest_id: str,
    branch: Optional[str] = None,
    output_path: Optional[Path] = None,
    other_args: Optional[list[str]] = None,
):
    """
    Executes DepotDownloader for the given parameters.

    Args:
        app_id: The AppID to download
        depot_id: The DepotID for which the manifest belongs
        manifest_id: The ManifestID to download
        branch: The branch (or nothing for public) to pull from
        output_path: The output path to write the files to
        other_args: The other args to send to DepotDownloader
    """

    steam_username = os.environ["DEPOTDOWNLOADER_USERNAME"]
    argslist = [
        "depotdownloader",
        "-username",
        steam_username,
        "-remember-password",
        "-app",
        app_id,
        "-depot",
        depot_id,
        "-manifest",
        manifest_id,
    ]

    if branch is not None and len(branch) > 0:
        argslist.append("-beta")
        argslist.append(branch)

    if output_path is not None and str(output_path) != "":
        argslist.append("-dir")
        argslist.append(str(output_path))

    if other_args is not None and len(other_args) > 0:
        argslist.extend(other_args)
        logger.trace(f"Adding other args: {other_args}")

    logger.info("[DepotDownloader] Processing manifest {}", manifest_id)
    logger.debug(
        "App ID: {} | Depot ID: {} | Manifest ID: {} | Branch: {}",
        app_id,
        depot_id,
        manifest_id,
        branch if branch else "public",
    )
    util.call_external_process("DepotDownloader", argslist, log_to_file=True)
