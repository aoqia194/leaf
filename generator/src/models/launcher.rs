use std::collections::HashMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::models::shared::Parseable;

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Download {
    pub(crate) sha1: String,
    pub(crate) size: u64,
    pub(crate) url: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Downloads {
    pub(crate) client: Vec<Download>,
    pub(crate) server: Vec<Download>,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RuleArgOs {
    pub(crate) arch: String,
    pub(crate) name: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Rule {
    pub(crate) action: String,
    pub(crate) features: Vec<HashMap<String, bool>>,
    pub(crate) os: RuleArgOs,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct RuleArg {
    pub(crate) rules: Vec<Rule>,
    pub(crate) value: Value,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LauncherManifestArgs {
    pub(crate) game: Vec<Value>,
    pub(crate) jvm: Vec<Value>,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LibraryArtifact {
    pub(crate) path: String,
    pub(crate) sha1: String,
    pub(crate) size: u64,
    pub(crate) url: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LibraryEntry {
    pub(crate) name: String,
    pub(crate) rules: Vec<Rule>,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LauncherManifestAssetIndex {
    pub(crate) sha1: String,
    pub(crate) size: u64,
    pub(crate) url: String,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LauncherManifest {
    pub(crate) arguments: Option<LauncherManifestArgs>,
    pub(crate) asset_index: LauncherManifestAssetIndex,
    pub(crate) java_version: String,
    pub(crate) libraries: Vec<LibraryEntry>,
    pub(crate) main_class: String,
    pub(crate) release_time: String,
    pub(crate) time: String,
    pub(crate) id: String,
}

impl Parseable for LauncherManifest {}
