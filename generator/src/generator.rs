use std::{
    collections::HashMap,
    fs::{self, File},
    io::BufWriter,
    path::PathBuf,
};

use crate::{
    Cli,
    constants::{
        GAME_VERSIONS_JSON, INDEXES_URL, MANIFESTS_URL, PlatformDepot, VERSION_MANIFEST_JSON,
    },
    models::{
        external::{steam_depot::DepotManifest, version_table::VersionTable},
        indexes::{AssetIndexEntry, AssetIndexManifest},
        launcher::{LauncherManifest, LauncherManifestAssetIndex},
        shared::Parseable,
        version::{LatestVersion, VersionManifest, VersionManifestEntry},
    },
    parser, utils,
};
use anyhow::{Context, Error, Result, ensure};
use chrono::{DateTime, Utc};
use semver::Version;
use strum::IntoEnumIterator;
use tracing::{Level, debug, info, instrument, trace, warn};

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn version_manifest(
    platform: &PlatformDepot,
    depot_manifest: &DepotManifest,
    game_version: &Version,
    launcher_manifest: &PathBuf,
    out: &PathBuf,
) -> Result<()> {
    info!("Generating version manifest");

    let game_version_str = game_version.to_string();

    // Hash the launcher manifest (stored in version manifests)
    let manifest = {
        let (hash_str, bytes) = utils::file_to_sha1(launcher_manifest)?;
        ensure!(bytes > 0);

        let url = format!(
            "{}/{}/{}/{}.json",
            MANIFESTS_URL,
            platform.env(),
            platform.name(),
            &game_version_str
        );

        let version = VersionManifestEntry {
            id: game_version_str.to_owned(),
            url,
            hash: hash_str,
            time: utils::to_leaf_date(&Utc::now()),
            release_time: utils::to_leaf_date(&utils::from_depot_manifest_date(
                &depot_manifest.manifest_date,
            )),
        };

        // If it doesn't already exist, create a new one and done.
        // Otherwise, we need to edit the existing one.
        if !out.exists() {
            VersionManifest {
                latest: LatestVersion::new(game_version_str),
                versions: vec![version],
            }
        } else {
            let mut m = VersionManifest::parse_from_path(out)?;
            let _ = m
                .update(version, game_version)
                .context("Failed to update version manifest")?;
            m
        }
    };

    let f = File::create(out)?;
    let writer = BufWriter::new(f);
    let serialize_result =
        serde_json::to_writer(writer, &manifest).context("Failed to overwrite version manifest");

    debug!("Generated version manifest successfully");
    serialize_result
}

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn launcher_manifest_internal(
    platform: &PlatformDepot,
    manifest_date: &DateTime<Utc>,
    version_table: &VersionTable,
    game_version: &Version,
    asset_index: LauncherManifestAssetIndex,
) -> Result<LauncherManifest> {
    let version = version_table
        .versions
        .get(&game_version.to_string())
        .context("Failed to get game version in version table")?;
    let inherited = if let Some(inherits) = &version.inherits {
        version_table.versions.get(inherits)
    } else {
        None
    };

    Ok(LauncherManifest {
        arguments: if let Some(arguments) = &version.arguments {
            Some(arguments.to_owned())
        } else if let Some(inherited) = inherited {
            Some(
                inherited
                    .arguments
                    .to_owned()
                    .context("Failed to get inherited version's arguments")?,
            )
        } else {
            None
        },
        asset_index,
        // TODO: In the future when the game upgrades Java version, need to check version minimums
        // Maybe include this in the game versions json too?
        java_version: "17".to_string(),
        libraries: if let Some(libs) = &version.libraries {
            libs.to_vec()
        } else {
            Vec::new()
        },
        // Ugly... maybe move this to version table model file and impl it??
        main_class: if let Some(main_class) = &version.main_class {
            if platform.env() == "client" {
                main_class.client.to_owned()
            } else {
                main_class.server.to_owned()
            }
        } else if let Some(inherited) = inherited {
            ensure!(
                inherited.main_class.is_some(),
                "Failed to get inherited version's arguments"
            );

            if platform.env() == "client" {
                inherited.main_class.as_ref().unwrap().client.to_owned()
            } else {
                inherited.main_class.as_ref().unwrap().server.to_owned()
            }
        } else {
            let mc = version_table
                .versions
                .values()
                .find_map(|v| v.main_class.as_ref())
                .context(
                    "Failed to find backup arguments list to populate launcher manifest with.",
                )?;
            if platform.env() == "client" {
                mc.client.to_owned()
            } else {
                mc.server.to_owned()
            }
        },
        release_time: utils::to_leaf_date(manifest_date),
        time: utils::to_leaf_date(&Utc::now()),
        id: game_version.to_string(),
    })
}

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn launcher_manifest(
    force: bool,
    platform: &PlatformDepot,
    depot_manifest: &DepotManifest,
    version_table: &VersionTable,
    game_version: &Version,
    asset_manifest: &PathBuf,
    out: &PathBuf,
) -> Result<()> {
    debug!("Parsing launcher manifest...");

    if !asset_manifest.exists() {
        return Err(Error::msg(
            "Asset manifest related to this launcher manifest doesn't exist",
        ));
    }

    let manifest_date = utils::from_depot_manifest_date(&depot_manifest.manifest_date);
    if !force && out.exists() {
        debug!(
            "Launcher manifest already exists @ {} - comparing the dates...",
            out.to_string_lossy()
        );

        let launcher_manifest = LauncherManifest::parse_from_path(out)?;
        let existing_manifest_date =
            utils::from_leaf_manifest_date(&launcher_manifest.release_time);
        if existing_manifest_date > manifest_date {
            debug!(
                "Launcher manifest already exists with game version {} at {:?}",
                game_version, out
            );
            return Ok(());
        }

        info!("Found launcher manifest with the same game version but an older release date.");
        info!("Overwriting this manifest with a newer version...");
    }

    let manifest = {
        let (hash, bytes) = utils::file_to_sha1(asset_manifest)?;
        let url = format!(
            "{}/{}/{}/{}.json",
            INDEXES_URL,
            platform.env(),
            platform.name(),
            game_version
        );
        let asset_index = LauncherManifestAssetIndex {
            hash,
            size: bytes as u64,
            url,
        };

        launcher_manifest_internal(
            platform,
            &manifest_date,
            version_table,
            game_version,
            asset_index,
        )?
    };

    let f = File::create(out)?;
    let writer = BufWriter::new(f);
    let res = serde_json::to_writer(writer, &manifest).context("Failed to write launcher manifest");

    debug!("Generated launcher manifest successfully");
    res
}

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn asset_manifest_internal(manifest: &DepotManifest) -> Result<AssetIndexManifest> {
    let mut objects: HashMap<String, AssetIndexEntry> = HashMap::new();
    for (path, entry) in &manifest.entries {
        let path = path.replace("\\", "/");
        objects.insert(
            path,
            AssetIndexEntry {
                hash: entry.hash.clone(),
                size: entry.size,
            },
        );
    }
    Ok(AssetIndexManifest { objects })
}

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn asset_manifest(force: bool, manifest: &DepotManifest, out: &PathBuf) -> Result<()> {
    if !force && out.exists() {
        warn!("Asset index manifest already exists");
        return Ok(());
    }

    let asset_index_manifest = asset_manifest_internal(manifest)?;

    trace!("Writing file to: {:?}", out);
    let file = File::create(out)?;
    let writer = BufWriter::new(file);
    let res = serde_json::to_writer(writer, &asset_index_manifest)
        .context("Failed to write asset index manifest");

    debug!("Generated asset manifest successfully");
    res
}

#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn generate_all(cli: &Cli) -> Result<()> {
    let version_table = VersionTable::parse_from_path(&cli.output_dir.join(GAME_VERSIONS_JSON))?;

    let manifests_path = cli.output_dir.join("manifests");
    let indexes_path = cli.output_dir.join("indexes");

    for platform in PlatformDepot::iter() {
        let platform_name = platform.name();
        let platform_env = platform.env();
        let depot_id = platform.depot_id();
        let depot_path = cli.depots_dir.join(depot_id.to_string());

        debug!("Parsing depot manifests...");
        let depot_manifests = parser::parse_depot_manifests(&depot_path, &version_table)?;
        assert!(!depot_manifests.is_empty());

        info!("Generating leaf manifests...");
        for (version_str, depot_manifest) in &depot_manifests {
            trace!("Depot manifest version_str: {}", version_str);
            let game_version = Version::parse(version_str)?;

            let parent_indexes_path = indexes_path.join(platform_env).join(platform_name);
            let parent_manifests_path = manifests_path.join(platform_env).join(platform_name);

            let asset_manifest_file = parent_indexes_path.join(version_str.to_owned() + ".json");
            let launcher_manifest_file =
                parent_manifests_path.join(version_str.to_owned() + ".json");
            let version_manifest_file = parent_manifests_path.join(VERSION_MANIFEST_JSON);

            debug!("Creating directories for later population...");
            fs::create_dir_all(&parent_indexes_path)?;
            fs::create_dir_all(&parent_manifests_path)?;

            // This order matters very much!
            asset_manifest(cli.force, depot_manifest, &asset_manifest_file)
                .context("Failed to generate index manifest")?;
            launcher_manifest(
                cli.force,
                &platform,
                depot_manifest,
                &version_table,
                &game_version,
                &asset_manifest_file,
                &launcher_manifest_file,
            )
            .context("Failed to generate version manifest")?;
            version_manifest(
                &platform,
                depot_manifest,
                &game_version,
                &launcher_manifest_file,
                &version_manifest_file,
            )
            .context("Failed to generate version manifest")?;

            info!("Successfully generated manifests");
        }
    }

    Ok(())
}
