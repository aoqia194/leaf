"""
Contains generator functions to generate leaf manifests.
Calling the main function will parse the manifests.txt file.
"""

from hashlib import sha1
from pathlib import Path
from time import perf_counter

from loguru import logger

from leaf import parser, util
from leaf.constants import (
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
    BuildManifestManifests,
    BuildManifestManifestsEntry,
    DepotManifest,
    GameInfo,
    GamePlatform,
    IndexManifest,
    IndexManifestVersion,
    SteamInfo,
)


def generate_manifests(steam_info: SteamInfo):
    """
    Creates a build manifest by using the steam info to download and parse game files.
    Will write generated files to disk
    """

    game_platform = GamePlatform(steam_info.depot_id)

    decompiler_input, decompile_output_path, manifest_output_path = util.prepare_game_files(
        steam_info
    )

    logger.trace("Generating build manifest...")
    start = perf_counter()

    game_info = parser.parse_game_info(decompiler_input, decompile_output_path, game_platform)
    depot_manifest = parser.parse_depot_manifest(manifest_output_path)

    version_label = util.to_version_label(game_info, steam_info)

    asset_manifest_file = (
        INDEXES_PATH
        / game_platform.env.value
        / game_platform.platform.value
        / f"{version_label}.json"
    )
    asset_manifest = create_asset_manifest(asset_manifest_file, depot_manifest)
    asset_manifest.write(asset_manifest_file)

    asset_manifest_ref = create_asset_manifest_ref(asset_manifest_file, game_platform)

    build_manifest_file = MANIFESTS_PATH / f"{version_label}.json"
    build_manifest = create_build_manifest(
        version_label, steam_info, game_info, game_platform, depot_manifest, asset_manifest_ref
    )
    build_manifest.write(build_manifest_file)

    build_manifest_ref = create_build_manifest_ref(build_manifest_file, depot_manifest)

    index_json_file = MANIFESTS_PATH / "index.json"
    index_json = get_or_create_index_manifest(index_json_file)

    existing_latest = index_json.latest.get(steam_info.branch)
    if existing_latest and util.is_newer_version(existing_latest, version_label):
        logger.debug("Found newer version for index json")
        index_json.latest[steam_info.branch] = version_label

    # Only set version if there isn't one already
    if index_json.versions.get(version_label) is None:
        index_json.versions[version_label] = build_manifest_ref

    index_json.write(index_json_file, overwrite=True)

    stop = perf_counter()
    logger.info(f"Generated build manifest after {((stop - start) * 1000):.3f}ms")


def get_or_create_index_manifest(path: Path) -> IndexManifest:
    if path.exists():
        return IndexManifest.read(path)

    return IndexManifest(latest={}, versions={})


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
    logger.info(f"Created asset manifest after {((stop - start) * 1000):.3f}ms")

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

    indexes = BuildManifestAssetIndexes()

    index = BuildManifestAssetIndexesEntry(
        url=(f"{INDEXES_URL}/{str(asset_manifest_file.relative_to(INDEXES_PATH))}"),
        size=str(asset_manifest_file.stat().st_size),
        sha1=sha1(asset_manifest_file.read_bytes()).hexdigest(),
    )

    indexes.set_platform(game_platform.platform, index)

    stop = perf_counter()
    logger.info(f"Created asset manifest ref after {((stop - start) * 1000):.3f}ms")

    return indexes


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
    logger.info(f"Created asset manifest ref after {((stop - start) * 1000):.3f}ms")

    return version


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
            client=BuildManifestManifestsEntry(macos=[], linux=[], windows=[]),
            server=BuildManifestManifestsEntry(common=[], macos=[], linux=[], windows=[]),
        ),
        asset_indexes=asset_manifest_ref,
        arguments=game_info.arguments,
        release_time=depot_manifest.manifest_date,
        generate_time=GENERATE_DATE,
    )

    # Add current manifest id to Manifest manifests.
    # Type checking is required because of "safety"
    entry = data.manifests.get_environment(env).get_platform(platform)
    if entry is not None:
        entry.append(steam_info.manifest_id)

    stop = perf_counter()
    logger.info(f"Created build manifest ref after {((stop - start) * 1000):.3f}ms")

    return data
