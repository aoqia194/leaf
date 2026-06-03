"""
A module containing some parsing functions to compliment the generator
"""

from pathlib import Path
from time import perf_counter
from typing import Optional

from loguru import logger

from leaf import util
from leaf.constants import (
    CORE_CLASS_FILE,
    CORE_JAVA_FILE,
    GAME_VERSION_BUILD_NUMBER_STR,
    GAME_VERSION_PATCH_STR,
    GAME_VERSION_STR,
    GIT_BRANCH_ALT_STR,
    GIT_BRANCH_STR,
    GIT_HASH_STR,
    GIT_VERSION_JAVA_FILE,
    JAR_MANIFEST_FILE,
    REVISION_NUMBER_STR,
)
from leaf.models import (
    ArgumentRule,
    ArgumentRulePlatform,
    BuildManifestArguments,
    BuildManifestArgumentsEntry,
    DepotManifest,
    DepotManifestEntry,
    GameInfo,
    GamePlatform,
    LauncherConfig,
)


def parse_game_info(
    input_path: Path, decompile_output_path: Path, game_platform: GamePlatform
) -> GameInfo:
    """
    Parses given game files and creates a populated object.
    `input_path` can either be the path to the game jar or the zombie folder.
    """

    logger.trace("Parsing game info...")
    start = perf_counter()

    is_jar_format = input_path.is_file() and input_path.suffix == ".jar"
    game_folder = input_path.parent if is_jar_format else input_path

    core_java_path = decompile_output_path.joinpath(CORE_JAVA_FILE)
    core_class_path = game_folder.joinpath(CORE_CLASS_FILE)
    gitversion_java_path = decompile_output_path.joinpath(GIT_VERSION_JAVA_FILE)
    jar_manifest_path = game_folder.joinpath(JAR_MANIFEST_FILE)

    major: Optional[int] = None
    minor: Optional[int] = None
    patch: Optional[int] = None
    suffix: Optional[str] = None

    revision: Optional[str] = None

    with open(core_java_path, "r", encoding="utf-8") as f_:
        for line in f_:
            if (
                major is not None
                and minor is not None
                and patch is not None
                and revision is not None
            ):
                break

            if major is None or minor is None:
                args = util.find_at_pos(line, GAME_VERSION_STR, ")")
                if args is not None:
                    values = tuple(x.lstrip() for x in args.split(","))
                    major = int(values[0])
                    minor = int(values[1])
                    suffix = values[2][1:-1]
            elif patch is None:
                s = util.find_at_pos(line, GAME_VERSION_PATCH_STR, '"')
                if s is not None:
                    patch = int(s[1:])
                else:
                    # Search for the build number (found in older versions)
                    s = util.find_at_pos(line, GAME_VERSION_BUILD_NUMBER_STR, '"')
                    if s is not None:
                        patch = int(s[1:])

            if revision is None:
                s = util.find_at_pos(line, REVISION_NUMBER_STR, " ")
                if s is not None:
                    revision = s

    if patch is None:
        logger.warning("No patch found for build, using 0")
        patch = 0

    if major is None or minor is None or patch is None:
        raise RuntimeError(f"""
                Failed to parse Core: no major, minor, or patch found
                Major={major} Minor={minor} Patch={patch}
            """)

    git_branch: Optional[str] = None
    git_hash: Optional[str] = None

    if not revision and gitversion_java_path.exists():
        with open(gitversion_java_path, "r", encoding="utf-8") as f:
            for line in f:
                if git_branch is not None and git_hash is not None:
                    break

                if git_hash is None:
                    git_hash = util.find_at_pos(line, GIT_HASH_STR, '"')
                    continue

                if git_branch is None:
                    git_branch = util.find_at_pos(line, GIT_BRANCH_STR, '"')

                if git_branch is None:
                    args = util.find_at_pos(line, GIT_BRANCH_ALT_STR, '"')
                    if args is not None:
                        values = tuple(x.strip() for x in args.split(" "))

                        git_branch = values[0]
                        git_hash = values[1]
                        continue

        if git_branch is None or git_hash is None:
            raise RuntimeError("Failed to parse game info: no branch or hash found")

    class_version = util.get_class_version(core_class_path)

    # Parsing launcher config stuff

    launcher_manifests = [
        next(game_folder.rglob("**/ProjectZomboid64.json"), None),
        next(game_folder.rglob("**/ProjectZomboid32.json"), None),
    ]
    launcher_configs = [
        parse_launcher_config(m) for m in launcher_manifests if m is not None and m.exists()
    ]

    main_class: Optional[str] = None
    arguments: BuildManifestArguments = BuildManifestArguments(game=[], jvm=[])

    # If we are JAR format, we can optionally get the main class from the manifest
    # This is a backup option if there were no launcher manifests to read from
    if is_jar_format:
        # Also match the main class string in the manifest
        with open(jar_manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line:
                    continue

                if line.startswith("Main-Class: "):
                    main_class = line.removeprefix("Main-Class: ").rstrip()
                    logger.debug("Found main class in jar manifest")
                    break

        if main_class is None:
            raise RuntimeError("Failed to parse game info: no main class found in jar manifest")

    if len(launcher_configs) > 0:
        first_config_file = next((f for f in launcher_manifests if f is not None), None)
        first = next((c for c in launcher_configs if c is not None), None)
        if first_config_file is not None and first is not None:
            if main_class is None:
                main_class = first.main_class
                logger.debug("Found main class in launcher config")

            for arg in first.vm_args:
                stem = first_config_file.stem
                arguments.jvm.append(
                    BuildManifestArgumentsEntry(
                        value=arg,
                        rules=[
                            ArgumentRule(
                                allow=True,
                                platform=ArgumentRulePlatform(
                                    name=game_platform.platform.value,
                                    arch=f"x{stem[len("ProjectZomboid") :]}",
                                ),
                            )
                        ],
                    )
                )
            logger.debug("Found jvm arguments in launcher config")

    if main_class is None:
        # Just fall back to a hardcoded path because oh well.
        logger.warning("Using fallback main class")
        main_class = "zombie.gameStates.MainScreenState"

    o = GameInfo(
        major=major,
        minor=minor,
        patch=patch,
        git_branch=git_branch,
        git_hash=git_hash,
        revision=revision,
        class_version=class_version,
        main_class=main_class,
        arguments=arguments,
    )

    stop = perf_counter()
    logger.info(f"Parsed game info after {((stop - start) * 1000):.3f}ms")

    return o


def parse_launcher_config(input_file: Path) -> LauncherConfig:
    """
    Parses the launcher config whilst also removing unnecessary things.
    """

    logger.trace("Parsing launcher config...")
    start = perf_counter()

    config = LauncherConfig.read(input_file)

    # config.vm_args[:] = [
    #     arg for arg in config.vm_args if not arg.startswith("-Xms") and not arg.startswith("-Xmx")
    # ]

    stop = perf_counter()
    logger.info(f"Parsed launcher config after {((stop - start) * 1000):.3f}ms")

    return config


def parse_depot_manifest(input_file: Path) -> DepotManifest:
    logger.trace("Parsing depot manifest...")
    start = perf_counter()

    depot_id: Optional[str] = None
    manifest_id: Optional[str] = None
    manifest_date: Optional[str] = None
    num_files: Optional[str] = None
    num_chunks: Optional[str] = None
    num_bytes_disk: Optional[str] = None
    num_bytes_compressed: Optional[str] = None
    entries: list[DepotManifestEntry] = []

    with input_file.open("r", encoding="utf-8") as f:
        # Parse the header
        for _ in range(10):
            line = next(f).rstrip()

            if not line:
                continue

            if line.startswith("Content Manifest for Depot "):
                depot_id = line.removeprefix("Content Manifest for Depot ")
                continue

            if line.startswith("Manifest ID / date"):
                _, _, value = line.partition(" : ")
                manifest_id, _, manifest_date = value.rstrip().partition(" / ")
                manifest_date = util.manifest_date_to_standard_date(manifest_date)
                continue

            if line.startswith("Total number of files"):
                _, _, num_files = line.partition(" : ")
                continue

            if line.startswith("Total number of chunks"):
                _, _, num_chunks = line.partition(" : ")
                continue

            if line.startswith("Total bytes on disk"):
                _, _, num_bytes_disk = line.partition(" : ")
                continue

            if line.startswith("Total bytes compressed"):
                _, _, num_bytes_compressed = line.partition(" : ")
                continue

            # Assume it's the entries table header
            if "File SHA" in line:
                continue

            raise RuntimeError(
                "Found an unrecognisable line in the depot manifest header:\n\t{}", line
            )

        if (
            depot_id is None
            or manifest_id is None
            or manifest_date is None
            or num_files is None
            or num_chunks is None
            or num_bytes_disk is None
            or num_bytes_compressed is None
        ):
            raise RuntimeError(
                "Failed to parse the depot manifest: the header wasn't parsed completely"
            )

        # Parse the entries
        for line in f:
            line = line.lstrip()

            # Quick way to determine if a folder.
            # Skip folders because they will bloat up the entry list and don't have hashes anyway
            if line[0] == "0" and line[7] == "0" and line[9] == "0" and line[48] == "0":
                continue

            size, chunks, file_hash, flags, name = line.split(maxsplit=4)
            entries.append(
                DepotManifestEntry(
                    size=size,
                    chunks=chunks,
                    file_sha=file_hash,
                    flags=flags,
                    name=name.strip(),
                )
            )

    depot_manifest = DepotManifest(
        depot_id=depot_id,
        manifest_id=manifest_id,
        manifest_date=manifest_date,
        num_files=num_files,
        num_chunks=num_chunks,
        num_bytes_disk=num_bytes_disk,
        num_bytes_compressed=num_bytes_compressed,
        entries=entries,
    )

    stop = perf_counter()
    logger.info(f"Parsed depot manifest after {((stop - start) * 1000):.3f}ms")

    return depot_manifest
