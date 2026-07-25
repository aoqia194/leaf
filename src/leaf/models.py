import hashlib
import json
from dataclasses import astuple, dataclass, field, replace
from enum import Enum
from json import JSONDecodeError
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

from dataclasses_json import DataClassJsonMixin, LetterCase, config, dataclass_json
from deepmerge.merger import Merger
from deepmerge.strategy.core import STRATEGY_END
from loguru import logger

from leaf import util


def filtered_optional_field(default: Any = None):
    return field(default=default, metadata=config(exclude=lambda v: v is None))


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

            # If the replacement value is None, use the original val
            if nxt_val is None:
                updated_fields[name] = base_val
            else:
                updated_fields[name] = merger.merge(base_val, nxt_val)

        return replace(base, **updated_fields)  # pyright: ignore[reportArgumentType]

    return STRATEGY_END


@dataclass_json(letter_case=LetterCase.CAMEL)  # type: ignore
@dataclass(slots=True)
class BaseJsonDataClass(DataClassJsonMixin):
    def merge_generic[T](self: T, nxt: T) -> T:
        merger = Merger(
            type_strategies=[
                (list, "append"),
                (dict, "merge"),
            ],
            fallback_strategies=[merge_dataclass, "override"],
            type_conflict_strategies=[merge_dataclass, "override"],
        )

        return merger.merge(self, nxt)


@dataclass(slots=True)
class IOJsonDataClass(BaseJsonDataClass):
    @classmethod
    def read_file(cls, file: Path):
        try:
            return cls.from_json(file.read_text())
        except JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse {cls.__name__}: a JSON decode error has occurred"
            ) from e

    def write_file(
        self,
        file: Path,
        overwrite: bool = False,
        minify: bool = False,
        allow_null: bool = True,
        sort_keys: bool = False,
    ):
        """
        Takes a dataclass and writes it as json to a file.
        Will automatically overwrite if the file exists and `overwrite` is True.
        Will minify the output if `minify` is True.
        """

        start = perf_counter()

        if not overwrite and file.exists():
            raise RuntimeError(
                f"Writing {type(self).__name__} failed because file exists and overwrite was False"
            )

        with open(file, "w", encoding="utf-8") as f:
            if allow_null:
                f.write(
                    self.to_json(
                        indent=None if minify else 2,
                        allow_nan=False,
                        ensure_ascii=True,
                        sort_keys=sort_keys,
                        separators=(",", ":") if minify else None,
                    )
                )
            else:
                raw = self.to_dict()
                clean = util.remove_null_inplace(raw)

                f.write(
                    json.dumps(
                        clean,
                        indent=None if minify else 2,
                        allow_nan=False,
                        ensure_ascii=True,
                        sort_keys=sort_keys,
                        separators=(",", ":") if minify else None,
                    )
                )

        stop = perf_counter()
        logger.trace(f"Writing {type(self).__name__} took {((stop - start) * 1000):.3f}ms")

    def update_file(self, file: Path):
        """
        Updates a file that contains this class by generic-merging
            it with this class instance and then writing back the result.
        """

        if not file.exists():
            raise RuntimeError("Updating existing file failed because it didn't exist")

        existing = type(self).read_file(file)
        existing.merge_generic(self)
        existing.write_file(file, overwrite=True)


@dataclass(slots=True)
class SemVer:
    major: int
    minor: int
    patch: int
    branch: Optional[str]
    build_id: Optional[str]

    @classmethod
    def parse(cls, s: str):
        logger.trace("Parsing version: {}", s)

        if "-" in s:
            version_num, rest = s.split("-", 1)
        else:
            version_num = s
            rest = None

        major, minor, patch = map(int, version_num.split("."))

        branch = None
        build_id = None

        if rest is not None:
            if "+" in rest:
                branch, build_id = rest.split("+", 1)
            else:
                branch, build_id = rest.split(".", 1)

        return cls(
            major=major,
            minor=minor,
            patch=patch,
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


@dataclass(slots=True)
class SteamInfo(BaseJsonDataClass):
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
    launcher_config: LauncherConfig

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


@dataclass(slots=True)
class LauncherConfig(IOJsonDataClass):
    """
    Holds data that was parsed from a game launcher config
    """

    main_class: Optional[str] = filtered_optional_field()
    classpath: Optional[list[str]] = filtered_optional_field()
    vm_args: Optional[list[str]] = filtered_optional_field()
    windows: Optional[dict[str, Any]] = filtered_optional_field()


@dataclass(slots=True)
class AssetManifest(IOJsonDataClass):
    objects: dict[str, AssetManifestEntry]


@dataclass(slots=True)
class AssetManifestEntry(BaseJsonDataClass):
    hash: str
    size: str


@dataclass(slots=True)
class IndexManifest(IOJsonDataClass):
    latest: dict[str, str]
    """
    Holds the latest steam_branch->version info
    """
    versions: dict[str, IndexManifestVersion]


@dataclass(slots=True)
class IndexManifestVersion(BaseJsonDataClass):
    url: str
    size: str
    hash: str
    release_time: str
    generate_time: str


@dataclass(slots=True)
class BuildManifest(IOJsonDataClass):
    id: str
    """ The parsed version label for this build. """
    steam_branch: str
    """ A git commit hash. Is null on pre-b42 builds. """
    java_version: int
    """The Java version of the game's code"""
    main_class: MainClass
    """The main class/entrypoint of the game for Java"""
    manifests: BuildManifestManifests
    """The Steam manifest ids linked to this version"""
    asset_indexes: BuildManifestAssetIndexes
    """The asset index references that are stored"""
    class_path: list[str]
    """The entries on the JVM class path as found by the launcher config"""
    arguments: BuildManifestArguments
    """The arguments that can be found in the launcher config"""
    release_time: str
    """The time at which the game version was published"""
    generate_time: str
    """The time at which this manifest was generated"""
    libraries: list[Any]
    """ TODO: Implement. A list of libraries the game comes with. """
    git_branch: Optional[str] = filtered_optional_field()
    """ A git branch name. Is null on pre-b42 builds. """
    git_hash: Optional[str] = filtered_optional_field()
    """ The short git hash of the published commit. Is null on pre-b42 builds. """

    def merge_arguments(self, other: BuildManifestArguments):
        """
        Merges other into self.
        """

        self.arguments.game.extend(other.game)

        for k1, v1 in other.jvm.items():
            if v1 is None:
                raise RuntimeError("Oopsies!")

            v2 = self.arguments.jvm.get(k1)
            if v2 is None:
                self.arguments.jvm[k1] = v1
                continue

            if v1.rules != v2.rules:
                v2.rules.extend(v1.rules)

    def merge(self, other: BuildManifest):
        """
        Merges other into self.
        """

        # Prioritise other main class (bc >MACOS is more likely to have it)
        if self.main_class.client is None:
            self.main_class.client = other.main_class.client
        if self.main_class.server is None:
            self.main_class.server = other.main_class.server

        self.merge_arguments(other.arguments)
        self.asset_indexes = self.asset_indexes.merge_generic(other.asset_indexes)
        self.manifests = self.manifests.merge_generic(other.manifests)


@dataclass(slots=True)
class MainClass(BaseJsonDataClass):
    client: Optional[str]
    server: Optional[str]

    def get_env_field(self, env: Environment) -> str:
        return getattr(self, env.value)

    def set_env_field(self, env: Environment, value: Optional[str]):
        setattr(self, env.value, value)


@dataclass(slots=True)
class BuildManifestManifests(BaseJsonDataClass):
    client: BuildManifestManifestsEntry
    server: BuildManifestManifestsEntry

    def get_env_field(self, env: Environment) -> BuildManifestManifestsEntry:
        return getattr(self, env.value)


@dataclass(slots=True)
class BuildManifestManifestsEntry(BaseJsonDataClass):
    macos: list[str] = field(default_factory=list)
    linux: list[str] = field(default_factory=list)
    windows: list[str] = field(default_factory=list)
    common: Optional[list[str]] = filtered_optional_field()
    """
    Only appears for server depots!
    """

    def get_platform_field(self, platform: Platform) -> Optional[list[str]]:
        return getattr(self, platform.value)

    def set_platform_field(self, platform: Platform, value: Optional[list[str]]):
        setattr(self, platform.value, value)


@dataclass(slots=True)
class BuildManifestAssetIndexes(BaseJsonDataClass):
    client: BuildManifestAssetIndexesEntry
    server: BuildManifestAssetIndexesEntry

    def get_env_field(self, env: Environment) -> BuildManifestAssetIndexesEntry:
        return getattr(self, env.value)

    def set_env_field(self, env: Environment, value: BuildManifestAssetIndexesEntry):
        getattr(self, env.value)
        setattr(self, env.value, value)


@dataclass(slots=True)
class BuildManifestAssetIndexesEntry(BaseJsonDataClass):
    macos: Optional[BuildManifestAssetIndexesEntryValue] = filtered_optional_field()
    linux: Optional[BuildManifestAssetIndexesEntryValue] = filtered_optional_field()
    windows: Optional[BuildManifestAssetIndexesEntryValue] = filtered_optional_field()
    common: Optional[BuildManifestAssetIndexesEntryValue] = filtered_optional_field()
    """
    Only appears for server depots!
    """

    def get_platform_field(self, platform: Platform) -> BuildManifestAssetIndexesEntryValue:
        return getattr(self, platform.value)

    def set_platform_field(self, platform: Platform, value: BuildManifestAssetIndexesEntryValue):
        getattr(self, platform.value)
        setattr(self, platform.value, value)


@dataclass(slots=True)
class BuildManifestAssetIndexesEntryValue(BaseJsonDataClass):
    sha1: str
    size: str
    url: str


@dataclass(slots=True)
class BuildManifestArguments(BaseJsonDataClass):
    game: list[str]
    jvm: dict[str, Optional[BuildManifestArgumentsEntry]]


@dataclass(slots=True)
class BuildManifestArgumentsEntry(BaseJsonDataClass):
    rules: list[ArgumentRule]


@dataclass(slots=True)
class ArgumentRule(BaseJsonDataClass):
    allow: bool
    platform: ArgumentRulePlatform


@dataclass(slots=True)
class ArgumentRulePlatform(BaseJsonDataClass):
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
