use std::collections::HashMap;

use serde::Deserialize;

use crate::models::{
    launcher::{LauncherManifestArgs, LibraryEntry},
    shared::Parseable,
};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct VersionTableMainClass {
    pub(crate) client: String,
    pub(crate) server: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct VersionTableEntry {
    pub(crate) arguments: Option<LauncherManifestArgs>,
    pub(crate) inherits: Option<String>,
    pub(crate) libraries: Option<Vec<LibraryEntry>>,
    pub(crate) main_class: Option<VersionTableMainClass>,
    pub(crate) manifests: Vec<u64>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct VersionTable {
    pub(crate) versions: HashMap<String, VersionTableEntry>,
}

impl Parseable for VersionTable {}
