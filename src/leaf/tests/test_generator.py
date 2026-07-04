from leaf import generator, util
from leaf.models import (
    BuildManifestArguments,
    BuildManifestAssetIndexes,
    BuildManifestAssetIndexesEntry,
    DepotManifest,
    DepotManifestEntry,
    GameInfo,
    GamePlatform,
    SteamInfo,
)


def test_generate_version_manifest():
    def make_manifest(steam_info: SteamInfo):
        game_info = GameInfo(
            major=42,
            minor=19,
            patch=0,
            git_branch="steam/release",
            git_hash="1aa820d7bb66c4e55513cae04022bdacdac5b34e",
            class_version=69,
            main_class="zombie.gameStates.MainScreenState",
            class_path=[".", "projectzomboid.jar"],
            arguments=BuildManifestArguments(game=[], jvm={}),
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

        asset_manifest_ref = BuildManifestAssetIndexes(
            client=BuildManifestAssetIndexesEntry(), server=BuildManifestAssetIndexesEntry()
        )

        version_label = util.to_version_label(game_info, steam_info)
        manifest = generator.create_build_manifest(
            version_label, steam_info, game_info, game_platform, depot_manifest, asset_manifest_ref
        )

        return manifest

    m1 = make_manifest(
        SteamInfo(
            app_id="108600", depot_id="108602", manifest_id="6878798369135719314", branch="unstable"
        )
    )
    m2 = make_manifest(
        SteamInfo(
            app_id="108600", depot_id="108603", manifest_id="5411994706418009543", branch="unstable"
        )
    )
    m3 = make_manifest(
        SteamInfo(
            app_id="108600", depot_id="108604", manifest_id="6433165352605909512", branch="unstable"
        )
    )

    m1.merge(m2)
    m1.merge(m3)

    assert m1.id == "42.19.0-unstable+1aa820d"
    assert m1.steam_branch == "unstable"
    assert m1.git_branch == "steam/release"
    assert m1.git_hash == "1aa820d7bb66c4e55513cae04022bdacdac5b34e"
    assert m1.java_version == 25
    assert m1.main_class == "zombie.gameStates.MainScreenState"

    assert len(m1.manifests.client.macos) == 1
    assert len(m1.manifests.client.linux) == 1
    assert len(m1.manifests.client.windows) == 1
    assert m1.manifests.client.macos[0] == "6878798369135719314"
    assert m1.manifests.client.linux[0] == "5411994706418009543"
    assert m1.manifests.client.windows[0] == "6433165352605909512"
