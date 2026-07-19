"""
Contains generator functions to generate leaf manifests.
Calling the main function will parse the manifests.txt file.
"""

from hashlib import sha1
from pathlib import Path
from time import perf_counter
from typing import Optional

from loguru import logger

from leaf import parser, util
from leaf.constants import (
    CACHE_PATH,
    GENERATE_DATE,
    INDEXES_PATH,
    INDEXES_URL,
    MANIFESTS_PATH,
    MANIFESTS_URL,
)
from leaf.models import (
    AssetManifest,
    AssetManifestEntry,
    BuildManifest,
    BuildManifestAssetIndexes,
    BuildManifestAssetIndexesEntry,
    BuildManifestAssetIndexesEntryValue,
    BuildManifestManifests,
    BuildManifestManifestsEntry,
    DepotManifest,
    Environment,
    GameInfo,
    GamePlatform,
    IndexManifest,
    IndexManifestVersion,
    Platform,
    SteamInfo,
)

GENERATION_QUEUE: list[SteamInfo] = []


def generate(steam_info: SteamInfo, overwrite: bool = False):
    """
    Creates all of the manifests needed by using the steam info to download and parse game files.
    Will write generated files to disk!
    """

    game_platform = GamePlatform(steam_info.depot_id)
    logger.info(
        "Generating for: {} {} {}",
        game_platform.env.name,
        game_platform.platform.name,
        steam_info.manifest_id,
    )

    # Don't support non-COMMON platform on SERVER env directly.
    # This is because it's impossible to get the game version from non-COMMON sources
    #   because non-COMMON SERVER doesn't contain java code.
    # To remedy this, we delay non-COMMON generation until the next COMMON SERVER is being generated.
    # In this case, we assume that the COMMON platform
    #   is the same version as the non-COMMON platform preceeding it.
    if game_platform.env == Environment.SERVER and game_platform.platform != Platform.COMMON:
        logger.debug("Added entry to generation queue")
        GENERATION_QUEUE.append(steam_info)
        return

    # Generate the main manifest stuff

    output_path = CACHE_PATH / steam_info.manifest_id
    decompiler_input, decompile_output_path = util.prepare_game_files(
        steam_info, game_platform, output_path
    )
    game_info = parser.parse_game_info(decompiler_input, decompile_output_path, game_platform)
    version_label = util.to_version_label(game_info, steam_info)

    generate_internal(steam_info, game_info, game_platform, version_label)

    # Generate all of the manifests in the queue also (assume that they are the same build/version)
    # Only asset manifests for the time being because we don't need anything else.
    if game_platform.env == Environment.SERVER and len(GENERATION_QUEUE) > 0:
        for entry in GENERATION_QUEUE:
            entry_game_platform = GamePlatform(entry.depot_id)
            logger.info(
                "Generating entry in generation queue for: {} {} {}",
                entry_game_platform.env.name,
                entry_game_platform.platform.name,
                entry.manifest_id,
            )

            generate_internal(entry, game_info, entry_game_platform, version_label)
        GENERATION_QUEUE.clear()


def generate_internal(
    steam_info: SteamInfo,
    game_info: GameInfo,
    game_platform: GamePlatform,
    version_label: str,
):
    logger.trace("Generating build manifest...")
    start = perf_counter()

    output_path = CACHE_PATH / steam_info.manifest_id
    manifest_file = util.prepare_depot_manifest(steam_info, output_path)
    depot_manifest = parser.parse_depot_manifest(manifest_file)

    asset_manifest_ref = generate_asset_manifest(
        (
            INDEXES_PATH
            / game_platform.env.value
            / game_platform.platform.value
            / f"{version_label}.json"
        ),
        depot_manifest=depot_manifest,
        game_platform=game_platform,
    )

    build_manifest_file = MANIFESTS_PATH / f"{version_label}.json"
    build_manifest_ref = generate_build_manifest(
        build_manifest_file,
        version_label=version_label,
        asset_manifest_ref=asset_manifest_ref,
        steam_info=steam_info,
        game_info=game_info,
        depot_manifest=depot_manifest,
        game_platform=game_platform,
    )

    generate_index_manifest(
        (MANIFESTS_PATH / "index.json"),
        steam_info=steam_info,
        version_label=version_label,
        build_manifest_file=build_manifest_file,
        build_manifest_ref=build_manifest_ref,
    )

    stop = perf_counter()
    logger.trace(f"Generated build manifest after {((stop - start) * 1000):.3f}ms")


def generate_index_manifest(
    file: Path,
    steam_info: SteamInfo,
    version_label: str,
    build_manifest_file: Path,
    build_manifest_ref: IndexManifestVersion,
):
    # Create and write the manifest if overwrite or it doesn't exist
    # Otherwise, just parse the existing one
    if file.exists():
        index_json = IndexManifest.read_file(file)
    else:
        index_json = create_index_manifest()

    existing_latest = index_json.latest.get(steam_info.branch)
    if existing_latest is None or util.is_newer_version(existing_latest, version_label):
        logger.debug("Found newer version for index json")
        index_json.latest[steam_info.branch] = version_label

    # If there's no version, just add it.
    # If there's already a version, assume merging happened (file updated)
    #   and so update the hash and size!
    if index_json.versions.get(version_label) is None:
        index_json.versions[version_label] = build_manifest_ref
    else:
        v = index_json.versions[version_label]
        v.hash = sha1(build_manifest_file.read_bytes()).hexdigest()
        v.size = str(build_manifest_file.stat().st_size)

    index_json.write_file(file, overwrite=True)


def create_index_manifest() -> IndexManifest:
    return IndexManifest(latest={}, versions={})


def generate_asset_manifest(
    file: Path, depot_manifest: DepotManifest, game_platform: GamePlatform
) -> BuildManifestAssetIndexes:
    logger.trace("Generating asset manifest...")
    start = perf_counter()

    # Create and write the manifest if overwrite or it doesn't exist
    # Otherwise, just parse the existing one
    if file.exists():
        asset_manifest = AssetManifest.read_file(file)
    else:
        asset_manifest = create_asset_manifest(file, depot_manifest)
        asset_manifest.write_file(file, minify=True)

    stop = perf_counter()
    logger.trace(f"Generated asset manifest after {((stop - start) * 1000):.3f}ms")

    asset_manifest_ref = create_asset_manifest_ref(file, game_platform)
    return asset_manifest_ref


def create_asset_manifest(
    asset_manifest_file: Path, depot_manifest: DepotManifest
) -> AssetManifest:
    logger.trace("Creating asset manifest...")
    start = perf_counter()

    if not asset_manifest_file.parent.exists():
        asset_manifest_file.parent.mkdir(parents=True, exist_ok=True)

    data = AssetManifest(objects={})

    for entry in depot_manifest.entries:
        data.objects[entry.name] = AssetManifestEntry(hash=entry.file_sha, size=entry.size)

    stop = perf_counter()
    logger.trace(f"Created asset manifest after {((stop - start) * 1000):.3f}ms")

    return data


# shit function name but it refers to the asset indexes object used in the build manifest
def create_asset_manifest_ref(
    asset_manifest_file: Path, game_platform: GamePlatform
) -> BuildManifestAssetIndexes:
    if not asset_manifest_file.exists():
        raise RuntimeError(
            "Failed to populate asset index reference in build manifes"
            " because asset index doesn't exist"
        )

    logger.trace("Creating asset manifest ref...")
    start = perf_counter()

    indexes = BuildManifestAssetIndexes(
        client=BuildManifestAssetIndexesEntry(), server=BuildManifestAssetIndexesEntry()
    )

    index = BuildManifestAssetIndexesEntryValue(
        url=(f"{INDEXES_URL}/{str(asset_manifest_file.relative_to(INDEXES_PATH))}"),
        size=str(asset_manifest_file.stat().st_size),
        sha1=sha1(asset_manifest_file.read_bytes()).hexdigest(),
    )

    indexes.get_env_field(game_platform.env).set_platform_field(game_platform.platform, index)

    stop = perf_counter()
    logger.trace(f"Created asset manifest ref after {((stop - start) * 1000):.3f}ms")

    return indexes


def generate_build_manifest(
    file: Path,
    version_label: str,
    asset_manifest_ref: BuildManifestAssetIndexes,
    steam_info: SteamInfo,
    game_info: GameInfo,
    depot_manifest: DepotManifest,
    game_platform: GamePlatform,
) -> IndexManifestVersion:
    logger.trace("Generating build manifest...")
    start = perf_counter()

    # if not overwrite and file.exists():
    #     logger.info("Skipping build manifest generation: it already exists!")
    #     return None

    build_manifest = create_build_manifest(
        version_label, steam_info, game_info, game_platform, depot_manifest, asset_manifest_ref
    )

    if file.exists():
        logger.debug("Build manifest already exists, begin merging!")
        existing_build_manifest = BuildManifest.read_file(file)
        existing_build_manifest.merge(build_manifest)
        build_manifest = existing_build_manifest

    build_manifest.write_file(file, overwrite=True)

    stop = perf_counter()
    logger.trace(f"Generated build manifest after {((stop - start) * 1000):.3f}ms")

    build_manifest_ref = create_build_manifest_ref(file, depot_manifest)
    return build_manifest_ref


def create_build_manifest(
    version_label: str,
    steam_info: SteamInfo,
    game_info: GameInfo,
    game_platform: GamePlatform,
    depot_manifest: DepotManifest,
    asset_manifest_ref: BuildManifestAssetIndexes,
) -> BuildManifest:
    """
    Creates a build manifest based on the given input
    """

    logger.trace("Creating build manifest...")
    start = perf_counter()

    platform = game_platform.platform
    env = game_platform.env

    data = BuildManifest(
        id=version_label,
        steam_branch=steam_info.branch,
        git_branch=game_info.git_branch,
        git_hash=game_info.git_hash,
        java_version=game_info.class_version - 44,
        main_class=game_info.main_class,
        manifests=BuildManifestManifests(
            client=BuildManifestManifestsEntry(),
            server=BuildManifestManifestsEntry(common=[]),
        ),
        asset_indexes=asset_manifest_ref,
        arguments=game_info.arguments,
        class_path=game_info.class_path,
        release_time=depot_manifest.manifest_date,
        generate_time=GENERATE_DATE,
    )

    # Add current manifest id to Manifest manifests.
    # Type checking is required because of "safety"
    entry = data.manifests.get_environment_field(env).get_platform_field(platform)
    if entry is not None:
        entry.append(steam_info.manifest_id)

    stop = perf_counter()
    logger.trace(f"Created build manifest after {((stop - start) * 1000):.3f}ms")

    return data


def create_build_manifest_ref(file: Path, depot_manifest: DepotManifest) -> IndexManifestVersion:
    if not file.exists():
        raise RuntimeError(
            "Failed to populate index.json version because build manifest doesn't exist"
        )

    logger.trace("Creating build manifest ref...")
    start = perf_counter()

    version = IndexManifestVersion(
        url=(f"{MANIFESTS_URL}/{str(file.relative_to(MANIFESTS_PATH))}"),
        size=str(file.stat().st_size),
        hash=sha1(file.read_bytes()).hexdigest(),
        release_time=depot_manifest.manifest_date,
        generate_time=GENERATE_DATE,
    )

    stop = perf_counter()
    logger.trace(f"Created build manifest ref after {((stop - start) * 1000):.3f}ms")

    return version
