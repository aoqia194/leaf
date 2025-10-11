#[cfg(test)]
mod tests {
    use chrono::{Datelike, Timelike};
    use tracing_test::traced_test;

    use crate::utils;

    // TODO: Unfortunately, the generator isn't so generic as the parser.
    // Writing tests for the generator is much harder and will require some code refactoring.
    // Mainly to separate physical and virtual files/data.
    // To do this, I want to move the generator functions to the data structs like how the parser is.

    #[traced_test]
    #[test]
    fn parse_depot_manifest_date_test() {
        let t = String::from("07/16/2025 17:10:33");
        let p = utils::from_depot_manifest_date(&t);
        assert_eq!(p.day(), 16);
        assert_eq!(p.month(), 7);
        assert_eq!(p.year(), 2025);
        assert_eq!(p.hour(), 17);
        assert_eq!(p.minute(), 10);
        assert_eq!(p.second(), 33);
    }

    #[traced_test]
    #[test]
    fn parse_leaf_manifest_date_test() {
        let t = String::from("2025-07-16T17:10:33Z");
        let p = utils::from_leaf_manifest_date(&t);
        assert_eq!(p.day(), 16);
        assert_eq!(p.month(), 7);
        assert_eq!(p.year(), 2025);
        assert_eq!(p.hour(), 17);
        assert_eq!(p.minute(), 10);
        assert_eq!(p.second(), 33);
    }
}
