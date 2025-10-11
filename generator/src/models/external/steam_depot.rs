use std::collections::HashMap;

use anyhow::{Context, Result};
use serde::Deserialize;
use tracing::{Level, debug, instrument, warn};

use crate::{
    constants::{DEPOT_ENTRY_REGEX, DEPOT_HEADER_REGEX},
    models::shared::IterParseable,
};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct DepotManifestEntry {
    pub(crate) size: u64,
    pub(crate) chunks: u64,
    pub(crate) hash: String,
    pub(crate) flags: u16,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct DepotManifest {
    pub(crate) depot_id: u32,
    pub(crate) manifest_id: u64,
    pub(crate) manifest_date: String,
    pub(crate) num_files: u64,
    pub(crate) num_chunks: u64,
    pub(crate) bytes_disk: u64,
    pub(crate) bytes_compressed: u64,
    /// Holds a map of path:entry
    pub(crate) entries: HashMap<String, DepotManifestEntry>,
}

impl IterParseable for DepotManifest {
    #[instrument(level = Level::TRACE, skip_all)]
    fn parse_from_iter<'a, I>(mut it: I) -> Result<Self>
    where
        I: Iterator<Item = &'a str>,
    {
        debug!("Parsing Steam depot manifest");

        // Parse depot header info.

        let mut manifest = {
            let header = it.by_ref().take(10).collect::<Vec<&'a str>>().join("\n");
            // trace!("Matching with regex: {}", DEPOT_HEADER_REGEX.as_str());
            let caps = DEPOT_HEADER_REGEX
                .captures(&header)
                .context("Failed to get depot header regex captures")?;

            DepotManifest {
                depot_id: caps["depot_id"].parse()?,
                manifest_id: caps["manifest_id"].parse()?,
                manifest_date: caps["manifest_date"].to_owned(),
                num_files: caps["num_files"].parse()?,
                num_chunks: caps["num_chunks"].parse()?,
                bytes_disk: caps["bytes_disk"].parse()?,
                bytes_compressed: caps["bytes_compressed"].parse()?,
                entries: HashMap::new(),
            }
        };

        // Parse the entries

        for line in it {
            let caps = DEPOT_ENTRY_REGEX
                .captures(line)
                .context("Failed to parse depot entry with regex")?;

            let size = caps["size"].parse()?;
            let flags = caps["flags"].parse()?;
            // Directories are noted as all 0's OR flag 40 and are skipped
            if flags == 40 || size == 0 {
                // trace!("Skipping directory entry");
                continue;
            }

            let chunks = caps["chunks"].parse()?;
            let hash = caps["hash"].to_string();
            let name = caps["name"].to_string();
            manifest.entries.insert(
                name.to_owned(),
                DepotManifestEntry {
                    chunks,
                    hash: hash.to_owned(),
                    size,
                    flags,
                },
            );

            // trace!(
            //     "Inserted depot manifest entry with key {} ->",
            //     name.to_owned()
            // );
        }

        manifest.entries.shrink_to_fit();
        Ok(manifest)
    }
}
