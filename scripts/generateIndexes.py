import pathlib
import sys
import json
import regex

regex.cache_all()

SCRIPT_DIR = pathlib.Path(__file__).parent
INDEXES_DIR = SCRIPT_DIR.parent.joinpath("indexes")

INDEXES_VER = "41.78.16"

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
                print("Found dir with size 0.")
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
    manifest_date = data[1][1] or ""
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

    json_data = json.dumps(table_data_formatted)
    with open(INDEXES_DIR.joinpath(f"{INDEXES_VER}.json"), "w", encoding="utf-8") as f:
        f.write(json_data)

    print("Done! :D")


if __name__ == "__main__":
    main()
