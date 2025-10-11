use std::collections::HashMap;

use serde::Serialize;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct AssetIndexEntry {
    pub(crate) hash: String,
    pub(crate) size: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct AssetIndexManifest {
    pub(crate) objects: HashMap<String, AssetIndexEntry>,
}
