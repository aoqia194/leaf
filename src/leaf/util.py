"""
A module containing some helpful utility functions
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Optional
from zipfile import ZipFile

from loguru import logger

from leaf import downloader
from leaf.constants import (
    CACHE_PATH,
    CORE_CLASS_FILE,
    DATE_FMT_8601,
    DATE_FMT_MANIFEST,
    FILELIST_FILE,
    GIT_VERSION_CLASS_FILE,
    JAR_MANIFEST_FILE,
    LOGS_PATH,
    VINEFLOWER_PATH,
)
from leaf.models import GameInfo, Platform, SemVer, SteamInfo


def manifest_date_to_standard_date(date: str) -> str:
    return datetime.strptime(date, DATE_FMT_MANIFEST).replace(tzinfo=UTC).strftime(DATE_FMT_8601)


def now_to_standard_date() -> str:
    return datetime.now(tz=UTC).strftime(DATE_FMT_8601)


def is_newer_version(old: str, new: str) -> bool:
    old_sv = SemVer.parse(old)
    new_sv = SemVer.parse(new)

    return new_sv.is_newer(old_sv)


def get_path(p: Optional[str], default: Optional[str | Path] = None) -> Path:
    if p:
        return Path(p.strip())

    if default:
        return Path(default)

    raise RuntimeError(
        "Failed to get path because the path was None and no valid default was specified"
    )


def format_path(p: Path, *args: str, **kwargs):
    return Path(str(p).format(args, kwargs))


def get_path_separator(platform: Platform) -> str:
    if platform in [Platform.COMMON, Platform.MACOS, Platform.LINUX]:
        return "/"
    elif platform == Platform.WINDOWS:
        return "\\"

    raise RuntimeError("Unknown platform")


def remove_null(data: object):
    match data:
        case dict():
            return {
                k: v for k, nxt in data.items() if (v := remove_null(nxt)) not in (None, {}, [])
            }
        case list():
            return [v for item in data if (v := remove_null(item)) not in (None, {}, [])]
        case _:
            return data


def remove_null_inplace(data):
    if isinstance(data, dict):
        # Snapshot keys to allow deletion during iteration
        for k in list(data.keys()):
            if isinstance(data[k], (dict, list)):
                remove_null_inplace(data[k])
            if data[k] in (None, {}, []):
                del data[k]
    elif isinstance(data, list):
        # Iterate backwards to safely delete items by index without shifting issues
        for i in range(len(data) - 1, -1, -1):
            if isinstance(data[i], (dict, list)):
                remove_null_inplace(data[i])
            if data[i] in (None, {}, []):
                del data[i]

    return data


def to_version_label(game_info: GameInfo, steam_info: SteamInfo) -> str:
    version_label = f"{game_info.major}.{game_info.minor}.{game_info.patch}-{steam_info.branch}"

    if game_info.revision is not None:
        version_label += f".{game_info.revision}"

    if game_info.git_hash is not None:
        version_label += f"+{game_info.git_hash[:7]}"

    return version_label


def get_vineflower_path() -> str:
    """
    Gets the location of vineflower if it is on the path
    """
    if VINEFLOWER_PATH is None:
        raise RuntimeError("Vineflower was not found on PATH")

    logger.trace("Found vineflower at path: {}", VINEFLOWER_PATH)
    return VINEFLOWER_PATH


def prepare_game_files(steam_info: SteamInfo):
    output_path = CACHE_PATH / steam_info.manifest_id
    manifest_output_path = (
        output_path / f"manifest_{steam_info.depot_id}_{steam_info.manifest_id}.txt"
    )
    files_output_path = output_path / "files"
    decompile_output_path = output_path / "decompile"

    jar_file = next(files_output_path.rglob("**/projectzomboid.jar"), None)
    core_class_path = next(files_output_path.rglob(f"**/{str(CORE_CLASS_FILE)}"), None)

    # Download the manifest
    if not manifest_output_path.exists():
        logger.trace("Downloading Steam manifest...")
        start = perf_counter()

        downloader.download(
            steam_info.app_id,
            steam_info.depot_id,
            steam_info.manifest_id,
            branch=steam_info.branch,
            output_path=manifest_output_path.parent,
            other_args=["-manifest-only"],
        )

        stop = perf_counter()
        logger.debug(f"Operation took {((stop - start) * 1000):.3f}ms")

    # Download the game files if there is no jar already here
    if not files_output_path.exists() or (jar_file is None and core_class_path is None):
        logger.trace("Downloading a few game files from Steam...")
        start = perf_counter()

        downloader.download(
            steam_info.app_id,
            steam_info.depot_id,
            steam_info.manifest_id,
            branch=steam_info.branch,
            output_path=files_output_path,
            other_args=["-filelist", FILELIST_FILE.name],
        )

        stop = perf_counter()
        logger.debug(f"Operation took {((stop - start) * 1000):.3f}ms")

        jar_file = next(files_output_path.rglob("**/projectzomboid.jar"), None)
        core_class_path = next(files_output_path.rglob(f"**/{str(CORE_CLASS_FILE)}"), None)

    decompiler_input = None
    if jar_file is not None:
        decompiler_input = jar_file
    elif core_class_path is not None:
        # Going to the parent of zombie/ folder
        decompiler_input = core_class_path.parent.parent.parent

    if decompiler_input is None:
        raise RuntimeError("Failed to locate java game code to decompile")

    if not decompile_output_path.exists():
        logger.trace("Decompiling game classes...")
        start = perf_counter()

        decompile(
            decompiler_input, decompile_output_path, only=[CORE_CLASS_FILE, GIT_VERSION_CLASS_FILE]
        )

        stop = perf_counter()
        logger.debug(f"Operation took {((stop - start) * 1000):.3f}ms")

    if (
        jar_file is not None
        and not jar_file.parent.joinpath(JAR_MANIFEST_FILE).exists()
        and not jar_file.parent.joinpath(CORE_CLASS_FILE).exists()
    ):
        # Extract some files out of the jar and put them alongside the jar
        logger.info("Extracting required files out of game jar...")
        with ZipFile(jar_file, "r") as zip_ref:
            zip_ref.extract(str(JAR_MANIFEST_FILE), path=jar_file.parent)
            zip_ref.extract(str(CORE_CLASS_FILE), path=jar_file.parent)

    return (decompiler_input, decompile_output_path, manifest_output_path)


def decompile(input_path: Path, output_path: Path, only: Optional[list[str | Path]] = None):
    """
    Decompiles a Java game jar or class package folder
    """
    is_already_decompiled = output_path.joinpath("zombie").exists()
    if is_already_decompiled:
        logger.warning("Found already-decompiled game jar")
        return

    argslist: list[str] = []

    vineflower_path = get_vineflower_path()
    if vineflower_path.endswith(".jar"):
        argslist.extend(["java", "-jar", vineflower_path])
    else:
        argslist.append(vineflower_path)

    if only is not None:
        argslist.extend([f"--only={str(f).replace(".class", "")}" for f in only])

    argslist.extend([str(input_path.resolve()), str(output_path)])

    logger.info(f"Decompiling {str(input_path)}...")
    call_external_process("vineflower", argslist, log_to_file=True)

    if not output_path.exists() or not any(output_path.iterdir()):
        raise RuntimeError("Failed to decompile because output was empty")


def call_external_process(
    name: str, args: str | list[str], log_to_file: bool = False
) -> Optional[str]:
    """
    Runs an external process with the given args list and returns the stdout
    """

    if not LOGS_PATH.exists():
        LOGS_PATH.mkdir(exist_ok=True)

    try:
        with open(LOGS_PATH.joinpath(f"{name}.log"), "w", encoding="utf-8") as f:
            res = subprocess.run(
                args,
                shell=(isinstance(args, str)),
                check=True,
                text=True,
                capture_output=(not log_to_file),
                stdout=(f if log_to_file else None),
                stderr=(f if log_to_file else None),
            )
        logger.trace(f"[{name}] Exited with code {res.returncode}")
        return res.stdout if not log_to_file else None
    except subprocess.CalledProcessError as e:
        logger.error(f"[{name}] Error: {e}")
        logger.info(f"Return code: {e.returncode}")
        logger.info(f"stderr: {e.stderr}")
        raise RuntimeError(f"Failed to download using external process {name}") from e


def get_class_version(file: Path) -> int:
    with file.open("rb") as f:
        f.seek(7)
        return ord(f.read(1))


def find_at_pos(s: str, prefix: str, terminator: str) -> Optional[str]:
    start = s.find(prefix)
    if start != -1:
        start += len(prefix)
        end = s.find(terminator, start)
        return s[start:end]

    return None
