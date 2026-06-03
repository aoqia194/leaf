from leaf import generator, util
from leaf.models import (
    BuildManifestArguments,
    BuildManifestAssetIndexes,
    DepotManifest,
    DepotManifestEntry,
    GameInfo,
    GamePlatform,
    SteamInfo,
)


def test_generate_version_manifest():
    steam_info = SteamInfo(
        app_id="108600", depot_id="108603", manifest_id="1323677770587120185", branch="unstable"
    )
    game_info = GameInfo(
        major=43,
        minor=67,
        patch=69,
        git_branch="mp/wips",
        git_hash="cafebae",
        class_version=69,
        main_class="zombie.gameStates.MainScreenState",
        arguments=BuildManifestArguments(game=[], jvm=[]),
    )
    game_platform = GamePlatform(steam_info.depot_id)
    depot_manifest = DepotManifest(
        depot_id=steam_info.depot_id,
        manifest_id=steam_info.manifest_id,
        manifest_date="04/20/2026 14:40:55",
        num_files="48686",
        num_chunks="42037",
        num_bytes_disk="11403638787",
        num_bytes_compressed="4662250368",
        entries=[
            DepotManifestEntry(
                size="1944",
                chunks="1",
                file_sha="57c74f0babb093cbfe759a19e512f9df4b9f6738",
                flags="0",
                name="projectzomboid.sh",
            )
        ],
    )

    asset_manifest_ref = BuildManifestAssetIndexes()

    version_label = util.to_version_label(game_info, steam_info)
    manifest = generator.create_build_manifest(
        version_label, steam_info, game_info, game_platform, depot_manifest, asset_manifest_ref
    )

    assert manifest.id == "43.67.69-unstable+cafebae"
    assert manifest.steam_branch == "unstable"
    assert manifest.git_branch == "mp/wips"
    assert manifest.git_hash == "cafebae"
    assert manifest.java_version == 25
    assert manifest.main_class == "zombie.gameStates.MainScreenState"
    assert manifest.manifests.client.linux[0] == "1323677770587120185"
