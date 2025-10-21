use std::{collections::HashMap, path::PathBuf};

use anyhow::Result;
use tracing::{Level, debug, info, instrument, warn};

use crate::{
    models::{
        external::{steam_depot::DepotManifest, version_table::VersionTable},
        shared::JsonIterParseable,
    },
    utils,
};

/// Parses all Steam depot manifests in the path and returns a map of (version, manifest)
#[instrument(level = Level::TRACE, skip_all)]
pub(crate) fn parse_depot_manifests(
    manifests: &Vec<PathBuf>,
    version_table: &VersionTable,
) -> Result<HashMap<String, DepotManifest>> {
    let mut uniques: HashMap<String, DepotManifest> = HashMap::new();

    debug!("Parsing depot manifests...");
    for entry in manifests {
        let manifest = DepotManifest::parse_from_path(&entry.to_path_buf())?;
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
