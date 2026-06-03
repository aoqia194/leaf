from leaf.models import BuildManifestManifests, BuildManifestManifestsEntry


def test_BuildManifestManifests_merge():
    first = BuildManifestManifests(
        client=BuildManifestManifestsEntry(macos=["456"], linux=["1234567890"], windows=[]),
        server=BuildManifestManifestsEntry(
            macos=[], linux=["0987654321"], windows=[], common=["123"]
        ),
    )
    second = BuildManifestManifests(
        client=BuildManifestManifestsEntry(macos=["444"], linux=["0987654321"], windows=["123"]),
        server=BuildManifestManifestsEntry(macos=["8888"], linux=[], windows=[], common=[]),
    )

    merged = first.merge_with(second)

    assert merged.client.macos == ["456", "444"]
    assert merged.client.linux == ["1234567890", "0987654321"]
    assert merged.client.windows == ["123"]
    assert merged.client.common == None
    assert merged.server.macos == ["8888"]
    assert merged.server.linux == ["0987654321"]
    assert merged.server.windows == []
    assert merged.server.common == ["123"]
