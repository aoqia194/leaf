#![feature(variant_count)]

use chrono::Utc;
use metadata::LevelFilter;
use quanta::{self, Instant};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env::{self, current_exe};
use std::io::{BufRead, BufReader, BufWriter, stdout};
use std::path::{Path, PathBuf};
use std::sync::LazyLock;
use std::{fs, u64};
use strum::FromRepr;
use tracing::*;
use tracing_appender::rolling::{RollingFileAppender, Rotation};
use tracing_subscriber::Layer;
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::fmt::layer;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;

#[derive(Serialize, Deserialize)]
struct AssetIndexObject {
    hash: String,
    size: u64,
}

#[derive(Serialize, Deserialize)]
struct AssetIndexManifest {
    objects: HashMap<String, AssetIndexObject>,
}

#[derive(Serialize, Deserialize)]
struct LauncherRules {
    action: String,
    features: Vec<HashMap<String, bool>>,
}

#[derive(Serialize, Deserialize)]
struct LauncherArgOs {
    name: String,
}

#[derive(Serialize, Deserialize)]
struct LauncherArgRule {
    os: LauncherArgOs,
    rules: Vec<LauncherRules>,
    value: Vec<String>,
}

#[derive(Serialize, Deserialize)]
enum LauncherArg {
    StringArg(String),
    RuleArg(LauncherArgRule),
}

#[derive(Serialize, Deserialize)]
struct LauncherArgs {
    game: Vec<LauncherArg>,
}

#[derive(Serialize, Deserialize)]
struct LauncherDownload {
    sha1: String,
    size: u64,
    url: String,
}

#[derive(Serialize, Deserialize)]
struct LauncherDownloads {
    client: Vec<LauncherDownload>,
    server: Vec<LauncherDownload>,
}

#[derive(Serialize, Deserialize)]
struct LauncherJavaVersion {
    component: String,
    major_version: u8,
}

#[derive(Serialize, Deserialize)]
struct LauncherLibraryArtifact {
    path: String,
    sha1: String,
    size: u8,
    url: String,
}

#[derive(Serialize, Deserialize)]
struct LauncherLibrary {
    downloads: LauncherLibraryArtifact,
    name: String,
    rules: Vec<LauncherRules>,
}

#[derive(Serialize, Deserialize)]
struct LauncherManifest {
    arguments: LauncherArgs,
    java_version: LauncherJavaVersion,
    libraries: Vec<LauncherLibrary>,
    main_class: String,
    release_time: String,
    time: String,
    version: String,
}

#[derive(Serialize, Deserialize)]
struct VersionEntry {
    id: String,
    url: String,
    time: String,
    release_time: String,
}

#[derive(Serialize, Deserialize)]
struct VersionLatest {
    release: String,
    snapshot: String,
}

#[derive(Serialize, Deserialize)]
struct VersionManifest {
    latest: VersionLatest,
    versions: Vec<VersionEntry>,
}

#[derive(Serialize, Deserialize)]
struct VersionTable {
    versions: HashMap<String, HashMap<String, String>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct DepotManifestEntry {
    size: u64,
    chunks: u32,
    sha1: String,
    flags: String,
}

#[derive(Debug)]
struct DepotManifest {
    depot_id: u64,
    manifest_id: u64,
    manifest_date: String,
    num_files: u32,
    num_chunks: u32,
    bytes_disk: u64,
    bytes_compressed: u64,
    entries: HashMap<String, DepotManifestEntry>,
}

#[derive(FromRepr, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(C)]
enum PlatformDepotId {
    MacClient = 108602,
    LinuxClient,
    WinClient,
    CommonServer = 380871,
    MacServer,
    LinuxServer,
    WinServer,
}

const INDEXES_URL: &str = "https://github.com/aoqia194/leaf/raw/refs/heads/main/indexes";
const MANIFESTS_URL: &str = "https://github.com/aoqia194/leaf/raw/refs/heads/main/manifests";

// common holds manifests for all platforms, like launcher version manifest
const CLIENT_PLATFORM_SUBDIRS: [&str; 3] = ["mac", "linux", "win"];
const SERVER_PLATFORM_SUBDIRS: [&str; 4] = ["common", "mac", "linux", "win"];
const CLIENT_DEPOT_SUBDIRS: [&str; 3] = ["108602", "108603", "108604"];
const SERVER_DEPOT_SUBDIRS: [&str; 4] = ["380871", "380872", "380873", "380874"];
const ENVIRONMENT_SUBDIRS: [&str; 2] = ["client", "server"];

const VERSION_MANIFEST_JSON: &str = "version_manifest.json";
const VERSION_TABLE_JSON: &str = "version_table.json";

const ARGS: LazyLock<Vec<String>> = LazyLock::new(|| env::args().collect());
const ARGS_MIN: usize = 2;
const ARGS_EXAMPLE: [&str; 2] = ["path/to/depots", "--force"];

static DEPOT_HEADER_REGEX: LazyLock<Regex> = LazyLock::new(|| {
    // (?:^Content Manifest for Depot (\d+)$)|(?:^Manifest ID \/ date\s*\:\s*(\d+)\s*\/\s*([^\n]+)$)|(?:^Total number of files\s*\:\s*(\d+)$)|(?:^Total number of chunks\s*\:\s*(\d+)$)|(?:^Total bytes on disk\s*\:\s*(\d+)$)|(?:^Total bytes compressed\s*\:\s*(\d+)$)|(?:^ *(Size)\s*(Chunks)\s*(File SHA)\s*(Flags)\s*(Name))
    Regex::new(r"(?:^Content Manifest for Depot (\d+)$)|(?:^Manifest ID \/ date\s*\:\s*(\d+)\s*\/\s*([^\n]+)$)|(?:^Total number of files\s*\:\s*(\d+)$)|(?:^Total number of chunks\s*\:\s*(\d+)$)|(?:^Total bytes on disk\s*\:\s*(\d+)$)|(?:^Total bytes compressed\s*\:\s*(\d+)$)").unwrap()
});
static DEPOT_ENTRY_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:^ *(\d+)\s*(\d+)\s*(\w+)\s*(\d+)\s*([^\n]*))").unwrap());

fn is_force() -> bool {
    return ARGS
        .get(2)
        .is_some_and(|s| s.as_str() == "--force" || s.as_str() == "-f");
}

fn get_utc_now() -> String {
    let time = Utc::now().naive_utc().to_string().replace(" UTC", "");
    let time = time[..19].to_string().replace(" ", "T") + "+00:00";

    warn!("UTC NOW {}", time);

    return time;
}

fn get_env_from_platform_dir(dir: &PathBuf) -> &str {
    return dir.parent().unwrap().file_name().unwrap().to_str().unwrap();
}

fn get_os_from_platform_dir(dir: &PathBuf) -> &str {
    return dir.file_name().unwrap().to_str().unwrap();
}

fn generate_indexes_manifest(
    depot: &DepotManifest,
    game_version: &String,
    out_platform_dir: &PathBuf,
) {
    let now = Instant::now();
    info!("Generating indexes manifest.");

    let out_file = out_platform_dir.join(game_version.to_owned() + ".json");
    let file = fs::File::create(out_file).unwrap();
    let writer = BufWriter::new(file);

    // Write depot entries to file.
    serde_json::to_writer(writer, &depot.entries)
        .expect("Failed to write json to indexes manifest");

    debug!(
        "Generating indexes manifest took {}ms",
        now.elapsed().as_millis()
    );
}

fn generate_launcher_manifest(
    depot: &DepotManifest,
    game_version: &String,
    out_platform_dir: &PathBuf,
) {
    let now = Instant::now();
    info!("Generating launcher manifest.");

    let mut manifest = LauncherManifest {
        arguments: LauncherArgs { game: Vec::new() },
        java_version: LauncherJavaVersion {
            component: String::from("java-runtime-delta"),
            major_version: 17,
        },
        libraries: Vec::new(),
        main_class: String::new(),
        release_time: depot.manifest_date.to_owned(),
        time: get_utc_now(),
        version: game_version.to_owned(),
    };

    if get_os_from_platform_dir(out_platform_dir) == "client" {
        manifest.main_class = String::from("zombie.gameStates.MainScreenState");
    } else {
        manifest.main_class = String::from("zombie.network.Server");
    }

    if game_version.as_str() >= "41.78.16" {
        manifest.java_version.major_version = 17;
    }

    let out_file = out_platform_dir.join(game_version.to_owned() + ".json");

    // If the manifest already exists and don't force overwrite it then do nothing
    if is_force() && fs::exists(out_file.to_owned()).is_ok() {
        debug!("Launcher manifest already exists. Skipping.");
        return;
    }

    let file = fs::File::create(out_file).unwrap();
    let writer = BufWriter::new(file);

    // Write depot entries to file.
    serde_json::to_writer(writer, &manifest).expect("Failed to write json to indexes manifest");

    debug!(
        "Generating launcher manifest took {}ms",
        now.elapsed().as_millis()
    );
}

fn generate_version_manifest(
    depot: &DepotManifest,
    game_version: &String,
    latest_versions: &(String, String),
    out_platform_dir: &PathBuf,
) {
    let now = Instant::now();
    info!("Generating version manifest.");

    let latest_version = latest_versions.0.to_owned();
    let latest_snapshot = latest_versions.1.to_owned();

    let out_file = out_platform_dir.join(VERSION_MANIFEST_JSON);

    let version_entry = VersionEntry {
        id: game_version.to_owned(),
        url: MANIFESTS_URL.to_owned()
            + "/"
            + get_env_from_platform_dir(out_platform_dir)
            + "/"
            + get_os_from_platform_dir(out_platform_dir)
            + "/"
            + game_version
            + ".json",
        time: get_utc_now(),
        release_time: depot.manifest_date.to_owned(),
    };

    // Preopen the file to check for invalid data and delete to retry.
    if out_file.to_owned().exists() {
        let file = fs::File::open(out_file.to_owned()).unwrap();
        let reader = BufReader::new(file);

        // Delete file to generate new valid manifest template.
        let version_manifest: Result<VersionManifest, serde_json::Error> =
            serde_json::from_reader(reader);
        if version_manifest.is_err() {
            fs::remove_file(out_file.to_owned()).unwrap();
        }
    }

    // Add version if needed if file already exists, else create.
    if out_file.to_owned().exists() {
        let file = fs::File::open(out_file.to_owned()).unwrap();
        let reader = BufReader::new(file);

        let mut version_manifest: VersionManifest = serde_json::from_reader(reader).unwrap();

        if version_manifest.latest.release != latest_version {
            version_manifest.latest.release = latest_version;
        }

        if version_manifest.latest.snapshot != latest_snapshot {
            version_manifest.latest.snapshot = latest_snapshot;
        }

        if game_version > &version_manifest.versions.first().unwrap().id {
            version_manifest.versions.insert(0, version_entry);
        } else if game_version < &version_manifest.versions.last().unwrap().id {
            version_manifest.versions.push(version_entry);
        } else {
            info!("Version already exists in version manifest.");
            return;
        }

        let file = fs::File::create(out_file).unwrap();
        let writer = BufWriter::new(file);
        serde_json::to_writer(writer, &version_manifest)
            .expect("Failed to edit and write json to version manifest");
    } else {
        let file = fs::File::create(out_file).unwrap();
        let writer = BufWriter::new(file);

        let versions: Vec<VersionEntry> = vec![version_entry];
        let manifest = VersionManifest {
            latest: VersionLatest {
                release: latest_version,
                snapshot: latest_snapshot,
            },
            versions,
        };

        serde_json::to_writer(writer, &manifest).expect("Failed to write json to version manifest");
    }

    debug!(
        "Generating version manifest took {}ms",
        now.elapsed().as_millis()
    );
}

fn get_depot_manifest(in_depots_dir: &PathBuf, depot_id: &str) -> PathBuf {
    let now = Instant::now();
    info!("Finding depot {} manifest.", depot_id);

    let subdir: PathBuf = fs::read_dir(in_depots_dir.join(depot_id))
        .unwrap()
        .nth(0)
        .unwrap()
        .unwrap()
        .path();
    let file: PathBuf = fs::read_dir(&subdir)
        .unwrap()
        .filter_map(|entry| {
            entry
                .as_ref()
                .unwrap()
                .file_type()
                .unwrap()
                .is_file()
                .then(|| entry.unwrap().path())
        })
        .collect::<Vec<PathBuf>>()
        .get(0)
        .unwrap()
        .to_owned();

    debug!(
        "Found depot manifest at path {:?} after {}ms",
        file.as_os_str(),
        now.elapsed().as_millis()
    );

    return file;
}

fn parse_depot_manifest(path: &PathBuf) -> DepotManifest {
    let now = Instant::now();
    info!("Parsing depot manifest.");

    let file = fs::File::open(path).expect("Failed to open depot file");
    let f = BufReader::new(file);
    let mut lines = f.lines().map(|l| l.unwrap());

    // Ungodly mess that works?
    let depot_id = DEPOT_HEADER_REGEX
        .captures(lines.nth(0).unwrap().as_str())
        .unwrap()[1]
        .parse::<u64>()
        .unwrap();
    lines.next().unwrap();
    let manifest_id_date = lines.next().unwrap();
    let manifest_id = DEPOT_HEADER_REGEX
        .captures(manifest_id_date.as_str())
        .unwrap()[2]
        .parse::<u64>()
        .unwrap();
    let manifest_date = DEPOT_HEADER_REGEX
        .captures(manifest_id_date.as_str())
        .unwrap()[3]
        .to_owned()
        .replace(" ", "T")
        + "+00:00";
    let num_files = DEPOT_HEADER_REGEX
        .captures(lines.next().unwrap().as_str())
        .unwrap()[4]
        .parse::<u32>()
        .unwrap();
    let num_chunks = DEPOT_HEADER_REGEX
        .captures(lines.next().unwrap().as_str())
        .unwrap()[5]
        .parse::<u32>()
        .unwrap();
    let bytes_disk = DEPOT_HEADER_REGEX
        .captures(lines.next().unwrap().as_str())
        .unwrap()[6]
        .parse::<u64>()
        .unwrap();
    let bytes_compressed = DEPOT_HEADER_REGEX
        .captures(lines.next().unwrap().as_str())
        .unwrap()[7]
        .parse::<u64>()
        .unwrap();
    lines.next().unwrap();
    lines.next().unwrap();

    // Create manifest data struct.
    let mut data = DepotManifest {
        depot_id,
        manifest_id,
        manifest_date,
        num_files,
        num_chunks,
        bytes_disk,
        bytes_compressed,
        entries: HashMap::new(),
    };

    // Process just the hash table entries
    for line in lines {
        let captures = DEPOT_ENTRY_REGEX.captures(line.as_str()).unwrap();
        let size = captures[1].parse::<u64>().unwrap();
        let chunks = captures[2].parse::<u32>().unwrap();
        let sha1 = captures[3].to_owned();
        let flags = captures[4].to_owned();
        let name = captures[5].to_owned();

        // If size is 0, the file is a directory.
        // We don't store directories because they're useless information.
        if size == 0 {
            continue;
        }

        data.entries.insert(name, DepotManifestEntry {
            size,
            chunks,
            sha1,
            flags,
        });
    }

    debug!(
        "Parsing depot manifest took {}ms",
        now.elapsed().as_millis()
    );
    return data;
}

fn get_version_table(file_path: &PathBuf) -> VersionTable {
    let now = Instant::now();
    info!("Finding version table.");

    // Open reader to the file.
    let file = fs::File::open(file_path).expect("Failed to find version table");
    let f = BufReader::new(file);

    // Let serde_json parse the file's json data.
    let version_table: VersionTable = serde_json::from_reader(f).unwrap();

    debug!(
        "Fetching version table took {}ms",
        now.elapsed().as_millis()
    );
    return version_table;
}

fn generate_server_manifests(
    version_table: &VersionTable,
    in_depots_dir: &PathBuf,
    out_manifests_dir: &PathBuf,
    out_indexes_dir: &PathBuf,
) {
    let now = Instant::now();

    for (i, depot_id) in SERVER_DEPOT_SUBDIRS.iter().enumerate() {
        let now2 = Instant::now();
        info!("Generating server manifests for depot {}", depot_id);

        let depot_file = get_depot_manifest(in_depots_dir, depot_id);
        let depot_manifest = parse_depot_manifest(&depot_file);

        let version_entry = version_table.versions.get(depot_id.to_owned()).unwrap();
        // release, snapshot
        let latest_versions = (
            version_entry
                .iter()
                .filter_map(|s| s.1.contains("-IWBUMS").eq(&false).then(|| s.1.to_owned()))
                .collect::<Vec<String>>()
                .get(0)
                .unwrap_or(&String::new())
                .to_owned(),
            version_entry
                .iter()
                .filter_map(|s| s.1.contains("-IWBUMS").then(|| s.1.to_owned()))
                .collect::<Vec<String>>()
                .get(0)
                .unwrap_or(&String::new())
                .to_owned(),
        );

        let game_version = version_entry
            .get(&depot_manifest.manifest_id.to_string())
            .unwrap()
            .to_owned();

        generate_indexes_manifest(
            &depot_manifest,
            &game_version,
            &out_indexes_dir
                .join(ENVIRONMENT_SUBDIRS[1])
                .join(SERVER_PLATFORM_SUBDIRS[i]),
        );

        generate_launcher_manifest(
            &depot_manifest,
            &game_version,
            &out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[1])
                .join(SERVER_PLATFORM_SUBDIRS[i]),
        );

        generate_version_manifest(
            &depot_manifest,
            &game_version,
            &latest_versions,
            &out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[1])
                .join(SERVER_PLATFORM_SUBDIRS[i]),
        );

        debug!(
            "Generating server manifests for depot {} took {}ms",
            depot_id,
            now2.elapsed().as_millis()
        );
    }

    debug!(
        "Generating platform manifests took {}ms",
        now.elapsed().as_millis()
    );
}

fn generate_client_manifests(
    version_table: &VersionTable,
    in_depots_dir: &PathBuf,
    out_manifests_dir: &PathBuf,
    out_indexes_dir: &PathBuf,
) {
    let now = Instant::now();

    for (i, depot_id) in CLIENT_DEPOT_SUBDIRS.iter().enumerate() {
        let now2 = Instant::now();
        info!("Generating client manifests for depot {}", depot_id);

        let depot_file = get_depot_manifest(in_depots_dir, depot_id);
        let depot_manifest = parse_depot_manifest(&depot_file);

        let version_entry = version_table.versions.get(depot_id.to_owned()).unwrap();
        // release, snapshot
        let latest_versions = (
            version_entry
                .iter()
                .filter_map(|s| s.1.contains("-IWBUMS").eq(&false).then(|| s.1.to_owned()))
                .collect::<Vec<String>>()
                .get(0)
                .unwrap_or(&String::new())
                .to_owned(),
            version_entry
                .iter()
                .filter_map(|s| s.1.contains("-IWBUMS").then(|| s.1.to_owned()))
                .collect::<Vec<String>>()
                .get(0)
                .unwrap_or(&String::new())
                .to_owned(),
        );

        let game_version = version_entry
            .get(&depot_manifest.manifest_id.to_string())
            .unwrap()
            .to_owned();

        generate_indexes_manifest(
            &depot_manifest,
            &game_version,
            &out_indexes_dir
                .join(ENVIRONMENT_SUBDIRS[0])
                .join(CLIENT_PLATFORM_SUBDIRS[i]),
        );

        generate_launcher_manifest(
            &depot_manifest,
            &game_version,
            &out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[0])
                .join(CLIENT_PLATFORM_SUBDIRS[i]),
        );

        generate_version_manifest(
            &depot_manifest,
            &game_version,
            &latest_versions,
            &out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[0])
                .join(CLIENT_PLATFORM_SUBDIRS[i]),
        );

        debug!(
            "Generating client manifests for depot {} took {}ms",
            depot_id,
            now2.elapsed().as_millis()
        );
    }

    debug!(
        "Generating platform manifests took {}ms",
        now.elapsed().as_millis()
    );
}

fn setup_logger() {
    let dir = current_exe().unwrap().parent().unwrap().join("logs/");

    let file_appender = RollingFileAppender::builder()
        .rotation(Rotation::HOURLY)
        .filename_suffix("log")
        .build(dir)
        .unwrap();

    let file_layer = layer()
        .with_writer(file_appender)
        .compact()
        .with_ansi(false)
        .with_file(true)
        .with_thread_ids(true)
        .with_thread_names(false)
        .with_line_number(true)
        .with_level(true)
        .with_target(true)
        .with_span_events(FmtSpan::FULL)
        .with_filter(LevelFilter::TRACE);

    let stdout_layer = layer()
        .with_writer(stdout)
        .with_file(false)
        .with_thread_names(false)
        .with_line_number(false)
        .with_target(true)
        .with_level(true)
        .with_span_events(FmtSpan::FULL)
        .with_filter(if cfg!(debug_assertions) {
            LevelFilter::TRACE
        } else {
            LevelFilter::INFO
        });

    tracing_subscriber::registry()
        .with(file_layer)
        .with(stdout_layer)
        .init();
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Handle program args
    if ARGS.len() < ARGS_MIN {
        panic!("Not enough arguments");
    } else if ARGS.len() > ARGS_EXAMPLE.len() + 1 {
        panic!("Too many arguments");
    }
    let in_depots_dir = PathBuf::from(&ARGS[1]);

    let exe_path = current_exe().unwrap();
    let exe_dir = exe_path.parent().unwrap();
    let leaf_dir = exe_dir
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
        .and_then(Path::parent)
        .unwrap();

    // Manifests output directories.
    let out_manifests_dir = leaf_dir.join("manifests");
    // Indexes output directories.
    let out_indexes_dir = leaf_dir.join("indexes");

    if !in_depots_dir.exists() {
        panic!("Input depots directory does not exist.");
    }

    // Create output directories if they don't exist.

    for platform in &CLIENT_PLATFORM_SUBDIRS {
        fs::create_dir_all(
            out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[0])
                .join(platform),
        )
        .expect("Failed to create client output directory.");

        fs::create_dir_all(out_indexes_dir.join(ENVIRONMENT_SUBDIRS[0]).join(platform))
            .expect("Failed to create client output directory.");
    }

    for platform in &SERVER_PLATFORM_SUBDIRS {
        fs::create_dir_all(
            out_manifests_dir
                .join(ENVIRONMENT_SUBDIRS[1])
                .join(platform),
        )
        .expect("Failed to create server output directory.");

        fs::create_dir_all(out_indexes_dir.join(ENVIRONMENT_SUBDIRS[1]).join(platform))
            .expect("Failed to create server output directory.");
    }

    setup_logger();
    info!("Hello! I am going to generate some manifests for you <3");
    trace!("force: {}", is_force());

    let version_table = get_version_table(&leaf_dir.join(VERSION_TABLE_JSON));
    generate_client_manifests(
        &version_table,
        &in_depots_dir,
        &out_manifests_dir,
        &out_indexes_dir,
    );
    generate_server_manifests(
        &version_table,
        &in_depots_dir,
        &out_manifests_dir,
        &out_indexes_dir,
    );

    info!("Done!");

    return Ok(());
}
