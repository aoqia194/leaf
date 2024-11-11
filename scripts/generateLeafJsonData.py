import pathlib
import sys
import json
from typing import TypedDict
import regex
import datetime

regex.cache_all()

SCRIPT_DIR = pathlib.Path(__file__).parent
INDEXES_DIR = SCRIPT_DIR.parent.joinpath("indexes")
MANIFESTS_DIR = SCRIPT_DIR.parent.joinpath("manifests")

VERSION_TABLE = {
    "7649580527091758034": "41.78.16",
    "6479059061804356642": "41.78.15",
    "6168490958362210069": "41.78.13",
}

VERSION_SNAPSHOT_TABLE = {
    "8862225121663207731": "41.78.13-IWBUMS",
}

LATEST_VER = list(VERSION_TABLE.values())[0]
LATEST_SNAPSHOT = list(VERSION_SNAPSHOT_TABLE.values())[0]
print(f"Latest Zomboid versions according to script (update if needed):\nLatest = {
      LATEST_VER}\nSnapshot = {LATEST_SNAPSHOT}")

DEPOT_MANIFEST = pathlib.Path(sys.argv[1]).resolve()
assert DEPOT_MANIFEST.exists()

REGEX_DEPOT_ID = regex.compile(r"(Content Manifest for Depot) (\d+)")
REGEX_MANIFEST_ID_DATE = regex.compile(r"(Manifest ID \/ date)\s*\:\s*(\d+)\s*\/\s*([^\n]+)")
REGEX_NUM_FILES = regex.compile(r"(Total number of files)\s*\:\s*(\d+)")
REGEX_NUM_CHUNKS = regex.compile(r"(Total number of chunks)\s*\:\s*(\d+)")
REGEX_BYTES_DISK = regex.compile(r"(Total bytes on disk)\s*\:\s*(\d+)")
REGEX_BYTES_COMPRESSED = regex.compile(r"(Total bytes compressed)\s*\:\s*(\d+)")
REGEX_TABLE_HEADER = regex.compile(r"(?:^ *(Size)\s*(Chunks)\s*(File SHA)\s*(Flags)\s*(Name))")
REGEX_TABLE_ENTRY = regex.compile(r"(?:^ *(\d+)\s*(\d+)\s*(\w+)\s*(\d+)\s*([^\n]*))")


class VersionNotFoundException(Exception):
    """Raised when the manifest version is not recognised.

    Args:
        Exception (_type_): _description_
    """

    def __init__(self, message):
        super().__init__(message)


class VersionManifestVersionNameInfo(TypedDict):
    id: str
    type: str
    time: str
    releaseTime: str
    manifestId: str
    url: str


class VersionManifestLatestNameInfo(TypedDict):
    release: str
    snapshot: str


class VersionManifestNameInfo(TypedDict):
    latest: VersionManifestLatestNameInfo
    versions: list[VersionManifestVersionNameInfo]


def get_regex_pattern_by_line(line_num):
    """_summary_

    Args:
        line_num (_type_): _description_

    Returns:
        _type_: _description_
    """

    if line_num == 0:
        return REGEX_DEPOT_ID
    elif line_num == 2:
        return REGEX_MANIFEST_ID_DATE
    elif line_num == 3:
        return REGEX_NUM_FILES
    elif line_num == 4:
        return REGEX_NUM_CHUNKS
    elif line_num == 5:
        return REGEX_BYTES_DISK
    elif line_num == 6:
        return REGEX_BYTES_COMPRESSED
    elif line_num == 8:
        return REGEX_TABLE_HEADER
    elif line_num >= 9:
        return REGEX_TABLE_ENTRY
    else:
        return None


def is_newer_version(older: str, newer: str):
    """Is version A newer than version B?

    Args:
        a (str): Older version to check against
        b (str): Version to check

    Returns:
        bool: True if B is newer than A
    """

    old_iwbums = older.find("IWBUMS")
    new_iwbums = newer.find("IWBUMS")

    older = older.removesuffix("-IWBUMS")
    newer = newer.removesuffix("-IWBUMS")

    old_vers = [int(x) for x in older.split(".")]
    new_vers = [int(x) for x in newer.split(".")]

    if -1 in old_vers or -1 in new_vers:
        return False

    if new_vers[0] > old_vers[0]:
        return True
    elif new_vers[1] > old_vers[1]:
        return True
    elif (new_vers[2] > old_vers[2]) or (new_vers[2] == old_vers[2] and new_iwbums and not old_iwbums):
        return True

    return False


def parse_table_data():
    data = []

    with open(DEPOT_MANIFEST, "r", encoding="utf-8") as f:
        for i, line in enumerate(f.readlines()):
            if i < 10:
                continue

            pattern = get_regex_pattern_by_line(i)
            if pattern is None:
                continue

            match = pattern.match(line)
            assert match is not None

            # dir check, dirs have size of 0
            if match.group(1) == "0":
                # print("Found dir with size 0.")
                continue

            data.append(match.groups())

    assert len(data) > 0
    assert data is not None

    return data


def parse_depot_data():
    data = []

    with open(DEPOT_MANIFEST, "r", encoding="utf-8") as f:
        for i, line in enumerate(f.readlines()):
            if i > 7:
                break

            # print("line = " + str(i))

            pattern = get_regex_pattern_by_line(i)
            if pattern is None:
                # print("Blank line found, skipping.")
                continue

            if i != 2:
                data.append(pattern.match(line)[2])
                continue

            manifest_id_date = pattern.match(line)
            assert manifest_id_date is not None
            data.append([manifest_id_date[2], manifest_id_date[3]])

    assert len(data) > 0
    assert data is not None

    return data


def main():
    """entrypoint"""

    if not INDEXES_DIR.exists():
        INDEXES_DIR.mkdir()

    data = parse_depot_data()
    assert data is not None

    depot_id = data[0] or -1
    manifest_id = data[1][0] or -1
    manifest_date = (data[1][1].replace(" ", "T") + "+00:00") or ""
    num_files = data[2] or -1
    num_chunks = data[3] or -1
    bytes_disk = data[4] or -1
    bytes_compressed = data[5] or -1

    print(f"Depot ID: {depot_id}")
    print(f"Manifest ID: {manifest_id}")
    print(f"Manifest Date: {manifest_date}")
    print(f"Number of files: {num_files}")
    print(f"Number of chunks: {num_chunks}")
    print(f"Bytes on disk: {bytes_disk}")
    print(f"Bytes compressed: {bytes_compressed}")

    if [-1, ""] in [depot_id, manifest_id, manifest_date, num_files, num_chunks, bytes_disk, bytes_compressed]:
        print("Failed to get manifest data.")
        return

    # Get index version and shit
    manifest_version = VERSION_SNAPSHOT_TABLE.get(manifest_id) or VERSION_TABLE.get(manifest_id) or None
    if manifest_version is None:
        raise VersionNotFoundException(
            "Failed to get manifest version."
            + "Most likely the manifest is newer than the supported"
            + "versions in the version table!")

    table_data = parse_table_data()
    table_data_formatted = {"objects": {}}
    for i, entry in enumerate(table_data):
        if i == 0:
            continue

        table_data_formatted["objects"][entry[4]] = {
            "size": entry[0],
            "chunks": entry[1],
            "hash": entry[2],
            "flags": entry[3],
            "name": entry[4],
        }
    assert table_data_formatted is not None

    # Write indexes data to file
    json_data = json.dumps(table_data_formatted)
    with open(INDEXES_DIR.joinpath(f"{manifest_version}.json"), "w", encoding="utf-8") as f:
        f.write(json_data)

    # Write manifests data to file, appending onto the previous manifest
    manifests_data: VersionManifestNameInfo = {
        "latest": {
            "release": LATEST_VER, "snapshot": LATEST_SNAPSHOT
        },
        "versions": []
    }

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    version_manifest = MANIFESTS_DIR.joinpath("version_manifest.json")

    # Defaults to generate new manifest file
    if not version_manifest.exists():
        manifests_data["versions"].append({
            "id": manifest_version,
            "type": "release",
            "time": now,
            "releaseTime": manifest_date,
            "manifestId": manifest_id,
            "url": f"https://github.com/aoqia194/leaf/raw/refs/heads/main/indexes/{manifest_version}.json",
        })
    else:
        with open(version_manifest, "r", encoding="utf-8") as f:
            data: VersionManifestNameInfo = json.load(f)

            # Update manifest versions if needed
            if is_newer_version(data["latest"]["release"], manifest_version):
                data["latest"]["release"] = LATEST_VER
            if is_newer_version(data["latest"]["snapshot"], manifest_version):
                data["latest"]["snapshot"] = LATEST_SNAPSHOT

            data["versions"].insert(0, {
                "id": manifest_version,
                "type": "release",
                "time": now,
                "releaseTime": manifest_date,
                "manifestId": manifest_id,
                "url": f"https://github.com/aoqia194/leaf/raw/refs/heads/main/indexes/{manifest_version}.json",
            })
            manifests_data = data

    json_data = json.dumps(manifests_data, indent=4)
    with open(version_manifest, "w", encoding="utf-8") as f:
        f.write(json_data)

    print("Done! :D")


if __name__ == "__main__":
    main()
