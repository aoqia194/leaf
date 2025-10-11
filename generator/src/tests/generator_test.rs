#[cfg(test)]
mod tests {
    use crate::{
        generator,
        models::{external::steam_depot::DepotManifest, shared::IterParseable},
        tests::test_constants::TEST_DEPOT_MANIFEST,
    };
    use std::io::Cursor;
    use tracing_test::traced_test;

    // TODO: Unfortunately, the generator isn't so generic as the parser.
    // Writing tests for the generator is much harder and will require some code refactoring.
    // Mainly to separate physical and virtual files/data.
    // To do this, I want to move the generator functions to the data structs like how the parser is.

    #[traced_test]
    #[test]
    fn generate_asset_manifest_test() {
        let manifest = DepotManifest::parse_from_reader(Cursor::new(&TEST_DEPOT_MANIFEST)).unwrap();

        let asset_manifest = generator::asset_manifest_internal(&manifest).unwrap();
        assert_eq!(asset_manifest.objects.len(), 4);

        let obj = &asset_manifest.objects[r"Project Zomboid.app/Contents/Info.plist"];
        assert_eq!(obj.hash, "5f77da0bcbf6a8a5571d85030b3cdf002d21da1e");
        assert_eq!(obj.size, 1700);
    }
}
