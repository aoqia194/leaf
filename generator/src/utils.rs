use std::{
    collections::HashMap,
    fs::File,
    io::{BufReader, Read},
    path::PathBuf,
};

use anyhow::{Context, Result};
use chrono::{DateTime, NaiveDateTime, Utc};
use sha1::{Digest, Sha1};
use tracing::{Level, debug, level_filters::LevelFilter, trace};
use tracing_subscriber::{Layer, layer::SubscriberExt};
use walkdir::WalkDir;

use crate::constants::{DT_FMT_8601, DT_FMT_MANIFEST};

/// Converts a Steam depot manifest date to a UTC date.
pub(crate) fn from_depot_manifest_date(s: &String) -> DateTime<Utc> {
    trace!("Attempting to parse date: {}", s);
    NaiveDateTime::parse_from_str(s, DT_FMT_MANIFEST)
        .expect("Failed to parse Steam depot manifest date")
        .and_utc()
}

/// Converts a leaf manifest date to a UTC date.
pub(crate) fn from_leaf_manifest_date(s: &str) -> DateTime<Utc> {
    NaiveDateTime::parse_from_str(s, DT_FMT_8601)
        .expect("Failed to parse leaf manifest date")
        .and_utc()
}

/// Converts a UTC date to a leaf manifest date (ISO-8601)
pub(crate) fn to_leaf_date(dt: &DateTime<Utc>) -> String {
    dt.format(DT_FMT_8601).to_string()
}

/// Walks a directory and finds all manifest_XXX_XXX.txt files
/// Returns the collected results
pub(crate) fn find_all_manifests(path: &PathBuf) -> Result<HashMap<u32, Vec<PathBuf>>> {
    let mut manifests = HashMap::new();

    debug!("Finding all depot manifests @ {:?}", path);
    for entry in WalkDir::new(path).min_depth(1).max_depth(3) {
        let entry = entry.context("Failed to get manifest file when walking dir")?;
        let entry_path = entry.path();
        let entry_stem = entry_path.file_stem();
        if !entry.file_type().is_file()
            || entry_path.to_string_lossy().contains(".DepotDownloader")
            || !entry_stem
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
        let entry_stem = entry_stem.unwrap();

        let depot_id = entry_stem
            .to_string_lossy()
            .split('_')
            .nth(1)
            .context("Failed to get depot id from manifest file name")?
            .parse::<u32>()
            .unwrap();

        manifests.entry(depot_id).or_insert_with(Vec::new);
        let _ = &manifests
            .get_mut(&depot_id)
            .unwrap()
            .push(entry_path.to_path_buf());
    }

    Ok(manifests)
}

/// Reads the entirety of a file's bytes into a Sha1 digest.
/// Returns the base-16 encoded sha1 string along with the amount of bytes that were processed.
pub(crate) fn file_to_sha1(path: &PathBuf) -> Result<(String, usize)> {
    let file = File::open(path)?;
    let mut reader = BufReader::new(file);

    let mut hasher = Sha1::new();
    let mut buf = [0u8; 4096];
    let mut bytes = 0;
    loop {
        let n = reader.read(&mut buf)?;
        if n == 0 {
            break;
        }

        hasher.update(&buf[..n]);
        bytes += n;
    }
    let digest = hasher.finalize();
    let mut encoded = [0u8; 40];
    let hash_str = base16ct::lower::encode_str(&digest, &mut encoded)?.to_owned();
    Ok((hash_str, bytes))
}

pub(crate) fn setup_logger(max_level: Level) -> Result<()> {
    let fmt_layer = tracing_subscriber::fmt::layer()
        .compact()
        .with_file(false)
        .with_line_number(false)
        .with_thread_ids(false)
        .with_target(false)
        .with_filter(LevelFilter::from(max_level));
    // let tracy_layer = tracing_tracy::TracyLayer::default();
    let subscriber = tracing_subscriber::registry().with(fmt_layer);
    // .with(tracy_layer);
    let _ = tracing::subscriber::set_global_default(subscriber);
    Ok(())
}
