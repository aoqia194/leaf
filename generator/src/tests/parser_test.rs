#[cfg(test)]
mod tests {
    use crate::{
        models::{
            external::{steam_depot::DepotManifest, version_table::VersionTable},
            shared::{IterParseable, Parseable},
        },
        parser,
        tests::test_constants::{TEST_DEPOT_MANIFEST, TEST_VERSION_TABLE},
    };
    use std::io::Cursor;
    use tracing_test::traced_test;

    #[traced_test]
    #[test]
    fn parse_depot_manifest_test() {
        let manifest = DepotManifest::parse_from_reader(Cursor::new(&TEST_DEPOT_MANIFEST)).unwrap();
        assert_eq!(manifest.depot_id, 108602);
        assert_eq!(manifest.manifest_id, 7984161633207534069);
        assert_eq!(manifest.manifest_date, "12/17/2024 17:50:27");
        assert_eq!(manifest.num_files, 51436);
        assert_eq!(manifest.num_chunks, 45197);
        assert_eq!(manifest.bytes_disk, 11307127538);
        assert_eq!(manifest.bytes_compressed, 5642932592);

        let entry = &manifest.entries[r"Project Zomboid.app\Contents\Info.plist"];
        assert_eq!(entry.size, 1700);
        assert_eq!(entry.chunks, 1);
        assert_eq!(entry.sha1, "5f77da0bcbf6a8a5571d85030b3cdf002d21da1e");
        assert_eq!(entry.flags, 0);
    }

    #[traced_test]
    #[test]
    fn parse_version_table_test() {
        let version_table =
            VersionTable::parse_from_reader(Cursor::new(&TEST_VERSION_TABLE)).unwrap();

        let v1 = version_table.versions.get("42.0.0-unstable.25057").unwrap();
        assert!(v1.arguments.is_none());
        assert!(v1.inherits.as_ref().is_some_and(|s| s == "41.78.16"));
        assert!(v1.libraries.is_none());
        assert!(v1.main_class.is_none());
        assert_eq!(v1.manifests[0], 7984161633207534069);
    }

    #[traced_test]
    #[test]
    fn find_game_version_test() {
        let version_table =
            VersionTable::parse_from_reader(Cursor::new(&TEST_VERSION_TABLE)).unwrap();
        let manifest = DepotManifest::parse_from_reader(Cursor::new(&TEST_DEPOT_MANIFEST)).unwrap();
        let game_version = parser::get_game_version(&version_table, &manifest).unwrap();
        assert_eq!(game_version, "42.0.0-unstable.25057");
    }
}
