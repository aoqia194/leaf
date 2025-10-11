use std::{
    fs::File,
    io::{BufReader, Read},
    path::PathBuf,
};

use anyhow::Result;
use chrono::{DateTime, NaiveDateTime, Utc};
use sha1::{Digest, Sha1};
use tracing::{Level, level_filters::LevelFilter, trace};
use tracing_subscriber::{Layer, layer::SubscriberExt};

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
