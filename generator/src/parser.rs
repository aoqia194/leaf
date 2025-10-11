use std::{collections::HashMap, path::PathBuf};

use anyhow::{Context, Result};
use tracing::{Level, debug, info, instrument, trace, warn};
use walkdir::WalkDir;

use crate::{
    models::{
        external::{steam_depot::DepotManifest, version_table::VersionTable},
        shared::IterParseable,
    },
    utils,
};

/// Parses all Steam depot manifests in the path and returns a map of (version, manifest)
#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn parse_depot_manifests(
    depot_path: &PathBuf,
    version_table: &VersionTable,
) -> Result<HashMap<String, DepotManifest>> {
    let mut uniques: HashMap<String, DepotManifest> = HashMap::new();

    debug!("Parsing depot manifests...");
    for entry in WalkDir::new(depot_path).min_depth(1).max_depth(2) {
        let entry = entry.context("Failed to get manifest file when walking dir")?;
        let entry_path = entry.path();
        if !entry.file_type().is_file()
            || !entry_path
                .file_stem()
                .unwrap()
                .to_string_lossy()
                .starts_with("manifest_")
            || entry_path.extension().unwrap() != "txt"
        {
            trace!(
                "Entry wasnt a file, didn't start with 'manifest_' {}",
                "or didn't have a txt extension."
            );
            continue;
        }

        debug!("Found depot manifest at {:?}", entry_path);

        let manifest = DepotManifest::parse_from_path(&entry_path.to_path_buf())?;
        let manifest_date = utils::from_depot_manifest_date(&manifest.manifest_date);

        let version_str = get_game_version(version_table, &manifest);
        if version_str.is_none() {
            info!(
                "Skipping manifest because: Failed to find game version for manifest: {}",
                manifest.manifest_id
            );
            continue;
        }
        let version_str = version_str.unwrap();

        let unique = uniques.get(&version_str);
        if unique.is_none()
            || manifest_date > utils::from_depot_manifest_date(&unique.unwrap().manifest_date)
        {
            debug!("Manifest was unique or contained a later build of the version.");
            let _ = uniques.insert(version_str, manifest);
        }
    }

    if uniques.is_empty() {
        warn!("Could not find any manifests in the folder");
    }

    Ok(uniques)
}

/// Gets the game version from a manifest by parsing the version table.
#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn get_game_version(
    version_table: &VersionTable,
    manifest: &DepotManifest,
) -> Option<String> {
    for (verstr, entry) in &version_table.versions {
        if entry.manifests.contains(&manifest.manifest_id) {
            return Some(verstr.to_owned());
        }
    }

    None
}
