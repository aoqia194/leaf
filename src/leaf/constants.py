"""
Stores constants used by other modules.
"""

import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from project_paths import paths, project_root

load_dotenv(project_root.joinpath(".env"))

VINEFLOWER_PATH: Optional[str] = os.environ.get(
    "VINEFLOWER_PATH", "vineflower" if shutil.which("vineflower") else None
)

OUT_PATH = project_root / "out"
CACHE_PATH = OUT_PATH / ".cache"
RESOLVED_PATH = OUT_PATH / "resolved"

DIST_PATH = project_root / "dist"
INDEXES_PATH = DIST_PATH / "indexes"
MANIFESTS_PATH = DIST_PATH / "manifests"

LOGS_PATH = project_root / "logs"

JAR_MANIFEST_FILE = Path("META-INF", "MANIFEST.MF")

CORE_CLASS_FILE = Path("zombie", "core", "Core.class")
GIT_VERSION_CLASS_FILE = Path("zombie", "GitVersion.class")

CORE_JAVA_FILE = Path("zombie", "core", "Core.java")
GIT_VERSION_JAVA_FILE = Path("zombie", "GitVersion.java")

GAME_VERSION_STR = "private static final GameVersion gameVersion = new GameVersion("
GAME_VERSION_PATCH_STR = 'return gameVersion + "'
GAME_VERSION_BUILD_NUMBER_STR = 'return gameVersion.toString() + "'
REVISION_NUMBER_STR = 'return " rev:'
GIT_BRANCH_STR = 'public static final String branchName = "'
GIT_BRANCH_ALT_STR = 'public static final String buildID = "'
GIT_HASH_STR = 'public static final String revision = "'

FILELIST_FILE = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
with FILELIST_FILE as _:
    _.writelines(
        [
            "regex:" + r".*(projectzomboid\.jar)" + "\n",
            "regex:" + f".*({str(CORE_CLASS_FILE)})" + "\n",
            "regex:" + f".*({str(GIT_VERSION_CLASS_FILE)})" + "\n",
            "regex:" + r".*(ProjectZomboid64\.json)" + "\n",
            "regex:" + r".*(ProjectZomboid32\.json)" + "\n",
        ]
    )

# DEPOT_HEADER_REGEX = re.compile(
#     "".join(
#         [
#             r"^",
#             r"\s*Content Manifest for Depot (?P<depot_id>\d+)",
#             r"\s*Manifest ID / date\s*: (?P<manifest_id>\d+) / (?P<manifest_date>\d+/\d+/\d+ \d+:\d+:\d+)",
#             r"\s*Total number of files\s*: (?P<num_files>\d+)",
#             r"\s*Total number of chunks\s*: (?P<num_chunks>\d+)",
#             r"\s*Total bytes on disk\s*: (?P<bytes_disk>\d+)",
#             r"\s*Total bytes compressed\s*: (?P<bytes_compressed>\d+)",
#         ]
#     )
# )

# DEPOT_ENTRY_REGEX = re.compile(
#     r"^\s*(?P<size>\d+)\s*(?P<chunks>\d+)\s*(?P<hash>\w+)\s*(?P<flags>\d+)\s*(?P<name>.+)"
# )

INDEXES_URL = f"https://github.com/aoqia194/leaf/raw/refs/heads/main/{os.path.relpath(INDEXES_PATH, paths.root)}"
MANIFESTS_URL = f"https://github.com/aoqia194/leaf/raw/refs/heads/main/{os.path.relpath(MANIFESTS_PATH, paths.root)}"

DATE_FMT_MANIFEST = r"%m/%d/%Y %H:%M:%S"
DATE_FMT_8601 = r"%Y-%m-%dT%H:%M:%SZ"

# Avoid recursive problem when importing util module
GENERATE_DATE = datetime.now(tz=UTC).strftime(DATE_FMT_8601)
