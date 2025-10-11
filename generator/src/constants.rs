use std::sync::LazyLock;

use regex::Regex;
use strum_macros::EnumIter;

pub(crate) const DT_FMT_MANIFEST: &str = "%m/%d/%Y %H:%M:%S";
pub(crate) const DT_FMT_8601: &str = "%Y-%m-%dT%H:%M:%SZ";

pub(crate) const INDEXES_URL: &str = "https://github.com/aoqia194/leaf/raw/refs/heads/main/indexes";
pub(crate) const MANIFESTS_URL: &str =
    "https://github.com/aoqia194/leaf/raw/refs/heads/main/manifests";

pub(crate) const VERSION_MANIFEST_JSON: &str = "version_manifest.json";
pub(crate) const GAME_VERSIONS_JSON: &str = "game_versions.json";

pub(crate) static DEPOT_HEADER_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(concat!(
        r"^",
        r"\s*Content Manifest for Depot (?<depot_id>\d+)",
        r"\s*Manifest ID / date\s*: (?<manifest_id>\d+) / (?<manifest_date>\d+/\d+/\d+ \d+:\d+:\d+)",
        r"\s*Total number of files\s*: (?<num_files>\d+)",
        r"\s*Total number of chunks\s*: (?<num_chunks>\d+)",
        r"\s*Total bytes on disk\s*: (?<bytes_disk>\d+)",
        r"\s*Total bytes compressed\s*: (?<bytes_compressed>\d+)",
    )).unwrap()
});
pub(crate) static DEPOT_ENTRY_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*(?<size>\d+)\s*(?<chunks>\d+)\s*(?<hash>\w+)\s*(?<flags>\d+)\s*(?<name>.+)")
        .unwrap()
});

#[derive(EnumIter)]
pub(crate) enum PlatformDepot {
    MacClient,
    LinuxClient,
    WindowsClient,
    CommonServer,
    MacServer,
    LinuxServer,
    WindowsServer,
}

impl PlatformDepot {
    pub(crate) const fn name(&self) -> &str {
        match *self {
            Self::CommonServer => "common",
            Self::MacClient | Self::MacServer => "mac",
            Self::LinuxClient | Self::LinuxServer => "linux",
            Self::WindowsClient | Self::WindowsServer => "win",
        }
    }

    pub(crate) const fn env(&self) -> &str {
        match *self {
            Self::MacClient | Self::LinuxClient | Self::WindowsClient => "client",
            Self::CommonServer | Self::MacServer | Self::LinuxServer | Self::WindowsServer => {
                "server"
            }
        }
    }

    pub(crate) const fn depot_id(&self) -> u32 {
        match *self {
            Self::MacClient => 108602,
            Self::LinuxClient => 108603,
            Self::WindowsClient => 108604,
            Self::CommonServer => 380871,
            Self::MacServer => 380872,
            Self::LinuxServer => 380873,
            Self::WindowsServer => 380874,
        }
    }
}
