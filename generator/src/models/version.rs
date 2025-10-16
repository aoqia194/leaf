use anyhow::{Context, Error, Result};
use semver::Version;
use serde::{Deserialize, Serialize};
use tracing::{Level, debug, instrument};

use crate::{models::shared::Parseable, utils};

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct VersionManifestEntry {
    pub(crate) id: String,
    pub(crate) url: String,
    pub(crate) sha1: String,
    pub(crate) time: String,
    pub(crate) release_time: String,
}

impl VersionManifestEntry {
    /// Updates the version manifest entry with a new one.
    /// Will only perform the update if the versions match and the new one is more recent.
    /// Returns if it was updated or not.
    pub(crate) fn update(&mut self, new: Self) -> Result<bool> {
        let date = utils::from_leaf_manifest_date(&self.release_time);
        let new_date = utils::from_leaf_manifest_date(&new.release_time);

        if self.id != new.id || date >= new_date {
            return Ok(false);
        }

        // The version can be the same but have a newer manifest.
        // For example, TIS not incrementing the game version when releasing a new build.
        debug!("Similar version found in manifest with older release time");

        self.id = new.id;
        self.release_time = new.release_time;
        self.sha1 = new.sha1;
        self.time = new.time;
        self.url = new.url;

        Ok(true)
    }
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct LatestVersion {
    pub(crate) release: Option<String>,
    pub(crate) unstable: Option<String>,
}

impl LatestVersion {
    /// Constructs a new LatestVersion with the correct version field populated.
    pub(crate) fn new(version: String) -> Self {
        if version.contains("unstable") {
            LatestVersion {
                release: None,
                unstable: Some(version),
            }
        } else {
            LatestVersion {
                release: Some(version),
                unstable: None,
            }
        }
    }

    /// Gets the correct version field for the given version.
    pub(crate) fn target(&mut self, version: &str) -> &mut Option<String> {
        if version.contains("unstable") {
            &mut self.unstable
        } else {
            &mut self.release
        }
    }

    /// Updates ***in place*** the LatestVersion of a given manifest.
    /// The manifest is updated if the latest version is non-existent or older than the input.
    /// Returns if the manifest was updated or not.
    pub(crate) fn update(&mut self, new: &Version) -> Result<bool> {
        let version_str = new.to_string();

        let target = self.target(&version_str);
        let needs_update = match target {
            Some(version) => *new > version.parse::<Version>()?,
            None => true,
        };

        if needs_update {
            *target = Some(version_str);
            return Ok(true);
        }

        Ok(false)
    }
}

/// Represents the `version_manifest.json` file for each depot platform.
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct VersionManifest {
    pub(crate) latest: LatestVersion,
    pub(crate) versions: Vec<VersionManifestEntry>,
}

impl VersionManifest {
    /// Adds a new version to the manifest.
    pub(crate) fn add(&mut self, new: VersionManifestEntry) -> Result<()> {
        let new_version = new.id.parse::<Version>()?;

        let mut pos = self.versions.len();
        for (i, e) in self.versions.iter().enumerate() {
            let curr = e.id.parse::<Version>()?;
            let next = self.versions[i + 1].id.parse::<Version>()?;

            if new_version == curr {
                return Err(Error::msg("Version already exists in the manifest"));
            } else if new_version < curr && new_version > next {
                pos = i;
                break;
            }
        }
        self.versions.insert(pos + 1, new);

        Ok(())
    }

    /// Updates ***in place*** a version manifest with a newer version entry.
    /// Returns true if modified an already-existing version.
    /// Returns false if created/inserted a new version.
    #[instrument(level = Level::TRACE, skip_all)]
    pub(crate) fn update(
        &mut self,
        new: VersionManifestEntry,
        game_version: &Version,
    ) -> Result<bool> {
        let game_version_str = game_version.to_string();

        let _ = self
            .latest
            .update(game_version)
            .context("Failed to update latest version for version manifest")?;

        // Insert version at the front or back of list if the version is unique to the manifest.
        // A short and quick assumption to prevent the loops later, but may break in the future.
        if let Some(first) = self.versions.first()
            && game_version > &first.id.parse()?
        {
            debug!("Version found was the latest, adding to the front of version list");
            self.versions.insert(0, new);
            return Ok(false);
        } else if let Some(last) = self.versions.last()
            && game_version < &last.id.parse()?
        {
            debug!("Version found was the oldest, adding to the end of version list");
            self.versions.push(new);
            return Ok(false);
        }

        // Version is not unique to the manifest so edit the existing one in place.
        let mut version_to_edit = self.versions.iter_mut().find(|v| v.id == game_version_str);
        let updated = match version_to_edit {
            Some(ref mut v) => v.update(new)?,
            None => self.add(new).is_ok(),
        };

        Ok(updated)
    }
}

impl Parseable for VersionManifest {}
