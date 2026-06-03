import hashlib
from dataclasses import astuple, dataclass, replace
from enum import Enum
from json import JSONDecodeError
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

import deepmerge
from dataclasses_json import DataClassJsonMixin, LetterCase, dataclass_json
from deepmerge.merger import Merger
from deepmerge.strategy.core import STRATEGY_END
from loguru import logger

from leaf import util


def merge_dataclass(
    merger: Merger,
    path: list,
    base: object,
    nxt: object,
):
    if type(base) is type(nxt) and hasattr(base, "__dataclass_fields__"):
        updated_fields = {}

        for name in base.__dataclass_fields__:  # pyright: ignore[reportAttributeAccessIssue]
            base_val = getattr(base, name)
            nxt_val = getattr(nxt, name)
            updated_fields[name] = merger.merge(base_val, nxt_val)

        return replace(base, **updated_fields)  # pyright: ignore[reportArgumentType]

    return STRATEGY_END


@dataclass(slots=True)
class SemVer:
    major: int
    minor: int
    patch: int
    branch: str
    build_id: str

    @classmethod
    def parse(cls, s: str):
        dash = s.index("-")
        plus = s.index("+")

        parts = s[:dash].split(".")
        branch = s[dash:plus]
        build_id = s[plus:]

        return cls(
            major=int(parts[0]),
            minor=int(parts[1]),
            patch=int(parts[2]),
            branch=branch,
            build_id=build_id,
        )

    def to_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def is_newer(self, other: SemVer):
        t1 = self.to_tuple()
        t2 = other.to_tuple()

        if t1 > t2:
            return True
        elif t1 < t2:
            return False

        return False


class Platform(Enum):
    COMMON = "common"
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"


class Environment(Enum):
    CLIENT = "client"
    SERVER = "server"


class GamePlatform(Enum):
    depot_id: str
    env: Environment
    platform: Platform

    MACOS_CLIENT = ("108602", Environment.CLIENT, Platform.MACOS)
    LINUX_CLIENT = ("108603", Environment.CLIENT, Platform.LINUX)
    WINDOWS_CLIENT = ("108604", Environment.CLIENT, Platform.WINDOWS)
    COMMON_SERVER = ("380871", Environment.SERVER, Platform.COMMON)
    MACOS_SERVER = ("380872", Environment.SERVER, Platform.MACOS)
    LINUX_SERVER = ("380873", Environment.SERVER, Platform.LINUX)
    WINDOWS_SERVER = ("380874", Environment.SERVER, Platform.WINDOWS)

    def __new__(cls, depot_id: str, env: Environment, platform: Platform):
        obj = object.__new__(cls)
        obj._value_ = depot_id
        obj.depot_id = depot_id
        obj.env = env
        obj.platform = platform

        return obj


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class SteamInfo(DataClassJsonMixin):
    app_id: str
    depot_id: str
    manifest_id: str
    branch: str


@dataclass(slots=True)
class GameInfo:
    """
    Holds a game revision's build info
    """

    major: int
    minor: int
    patch: int
    class_version: int
    main_class: str
    arguments: BuildManifestArguments

    git_branch: Optional[str] = None
    """ 
    An internal git branch found on b42 unstable releases 
    """
    git_hash: Optional[str] = None
    """ 
    A git commit hash found on b42 unstable releases 
    """
    revision: Optional[str] = None
    """ 
    A revision number found on early b42 unstable releases
    before `git_hash` and `git_branch` were a thing.
    """


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class LauncherConfig(DataClassJsonMixin):
    """
    Holds data that was parsed from a game launcher config
    """

    main_class: str
    classpath: list[str]
    vm_args: list[str]
    windows: Optional[dict[str, Any]] = None

    @classmethod
    def read(cls, file: Path):
        """
        Parses a game launcher config file into an object
        """

        try:
            with open(file, "r", encoding="utf-8") as f:
                return cls.from_json(f.read())
        except JSONDecodeError as e:
            raise RuntimeError(
                "Failed to parse game launcher config: a JSON decode error has occurred"
            ) from e


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class AssetManifest(DataClassJsonMixin):
    objects: dict[str, AssetManifestEntry]

    def write(self, file: Path, overwrite: bool = False):
        """
        Takes a Manifest and writes it as json to a file.
        Will automatically overwrite if the file exists and `overwrite` is True.
        """

        start = perf_counter()

        if not overwrite and file.exists():
            logger.warning(
                "Writing asset manifest failed because file exists and overwrite was False"
            )
            return

        with open(file, "w", encoding="utf-8") as f:
            f.write(
                util.remove_null_inplace(
                    self.to_json(
                        indent=None, allow_nan=False, ensure_ascii=True, separators=(",", ":")
                    )
                )
            )

        stop = perf_counter()
        logger.info(f"Writing AssetManifest took {((stop - start) * 1000):.3f}ms")


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class AssetManifestEntry(DataClassJsonMixin):
    hash: str
    size: str


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class IndexManifest(DataClassJsonMixin):
    latest: dict[str, str]
    """
    Holds the latest steam_branch->version info
    """
    versions: dict[str, IndexManifestVersion]

    @classmethod
    def read(cls, file: Path):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return cls.from_json(f.read())
        except JSONDecodeError as e:
            raise RuntimeError(
                "Failed to parse index manifest: a JSON decode error has occurred"
            ) from e

    def write(self, file: Path, overwrite: bool = False):
        """
        Takes in an instance and writes it as json to a file.
        Will automatically overwrite if the file exists and `overwrite` is True.
        """

        start = perf_counter()

        if not overwrite and file.exists():
            logger.warning("Writing index.json failed because file exists and overwrite was False")
            return

        with open(file, "w", encoding="utf-8") as f:
            f.write(
                util.remove_null_inplace(self.to_json(indent=2, allow_nan=False, ensure_ascii=True))
            )

        stop = perf_counter()
        logger.info(f"Writing index.json took {((stop - start) * 1000):.3f}ms")


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class IndexManifestVersion(DataClassJsonMixin):
    url: str
    size: str
    hash: str
    release_time: str
    generate_time: str


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifest(DataClassJsonMixin):
    """
    Holds data that was parsed from game files
    """

    id: str
    steam_branch: str
    git_branch: Optional[str]
    """ A git branch name. Is null on pre-b42 builds. """
    git_hash: Optional[str]
    """ A git commit hash. Is null on pre-b42 builds. """
    java_version: int
    """The Java version of the game's code"""
    main_class: str
    """The main class/entrypoint of the game for Java"""
    manifests: BuildManifestManifests
    """The Steam manifest ids linked to this version"""
    asset_indexes: BuildManifestAssetIndexes
    """The asset index references that are stored"""
    arguments: BuildManifestArguments
    """The arguments that can be found in the launcher config"""
    release_time: str
    """The time at which the game version was published"""
    generate_time: str
    """The time at which this manifest was generated"""

    def write(self, file: Path, merge: bool = True):
        """
        Takes a Manifest and writes it as json to a file.
        Will automatically merge if the file exists and `merge` is True.
        """

        start = perf_counter()

        other: Optional[BuildManifest] = None
        if merge and file.exists():
            with open(file, "r", encoding="utf-8") as f:
                other = BuildManifest.from_json(f.read())

            other.manifests.merge_with(self.manifests)

        with open(file, "w", encoding="utf-8") as f:
            f.write(
                util.remove_null_inplace(
                    (other or self).to_json(indent=2, allow_nan=False, ensure_ascii=True)
                )
            )

        stop = perf_counter()
        logger.info(f"Writing BuildManifest took {((stop - start) * 1000):.3f}ms")


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestManifests(DataClassJsonMixin):
    client: BuildManifestManifestsEntry
    server: BuildManifestManifestsEntry

    def get_environment(self, env: Environment):
        return getattr(self, env.value)

    def merge_with(self, nxt: BuildManifestManifests) -> BuildManifestManifests:
        merger = Merger(
            type_strategies=[
                (list, "append"),
                (dict, "merge"),
            ],
            fallback_strategies=[merge_dataclass, "override"],
            type_conflict_strategies=[merge_dataclass, "override"],
        )

        return merger.merge(self, nxt)


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestManifestsEntry(DataClassJsonMixin):
    macos: list[str]
    linux: list[str]
    windows: list[str]
    common: Optional[list[str]] = None
    """
    Only appears for server depots!
    """

    def get_platform(self, platform: Platform) -> Optional[list[str]]:
        return getattr(self, platform.value)


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestAssetIndexes(DataClassJsonMixin):
    macos: Optional[BuildManifestAssetIndexesEntry] = None
    linux: Optional[BuildManifestAssetIndexesEntry] = None
    windows: Optional[BuildManifestAssetIndexesEntry] = None
    common: Optional[BuildManifestAssetIndexesEntry] = None
    """
    Only appears for server depots!
    """

    def get_platform(self, platform: Platform) -> Optional[BuildManifestAssetIndexesEntry]:
        return getattr(self, platform.value)

    def set_platform(self, platform: Platform, value: BuildManifestAssetIndexesEntry):
        getattr(self, platform.value)
        setattr(self, platform.value, value)


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestAssetIndexesEntry(DataClassJsonMixin):
    sha1: str
    size: str
    url: str


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestArguments(DataClassJsonMixin):
    game: list[str]
    jvm: list[BuildManifestArgumentsEntry]


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BuildManifestArgumentsEntry(DataClassJsonMixin):
    value: str
    rules: list[ArgumentRule]


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class ArgumentRule(DataClassJsonMixin):
    allow: bool
    platform: ArgumentRulePlatform


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class ArgumentRulePlatform(DataClassJsonMixin):
    name: str
    arch: str


@dataclass(slots=True)
class DepotManifest:
    depot_id: str
    manifest_id: str
    manifest_date: str
    num_files: str
    num_chunks: str
    num_bytes_disk: str
    num_bytes_compressed: str
    entries: list[DepotManifestEntry]


@dataclass(slots=True)
class DepotManifestEntry:
    size: str
    chunks: str
    file_sha: str
    flags: str
    name: str

    def hash(self) -> str:
        return hashlib.sha1(" ".join([str(f) for f in astuple(self)]).encode()).hexdigest()
