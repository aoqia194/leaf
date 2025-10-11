use std::{
    any::type_name,
    fs::File,
    io::{BufRead, BufReader, Read},
    path::PathBuf,
};

use anyhow::{Context, Result, ensure};
use serde::Deserialize;
use tracing::debug;

pub(crate) trait Parseable: Sized + for<'de> Deserialize<'de> {
    fn parse_from_reader<R: Read>(reader: R) -> Result<Self> {
        let type_name = type_name::<Self>();
        debug!("Parsing {} object from reader", type_name);
        serde_json::from_reader(reader)
            .context(format!("Failed to parse {} from reader", type_name))
    }

    fn parse_from_file(file: &File) -> Result<Self> {
        let reader = BufReader::new(file);
        Self::parse_from_reader(reader)
    }

    fn parse_from_path(path: &PathBuf) -> Result<Self> {
        ensure!(
            path.exists(),
            format!("File doesn't exist at path: {}", path.to_str().unwrap())
        );
        let file = File::open(path)?;
        Self::parse_from_file(&file)
    }
}

pub(crate) trait IterParseable: Sized {
    fn parse_from_iter<'a, I>(it: I) -> Result<Self>
    where
        I: Iterator<Item = &'a str>;

    fn parse_from_string(s: &str) -> Result<Self> {
        Self::parse_from_iter(s.lines())
    }

    fn parse_from_reader<R: BufRead>(reader: R) -> Result<Self> {
        Self::parse_from_iter(
            reader
                .lines()
                .map_while(Result::ok)
                .collect::<Vec<String>>()
                .iter()
                .map(|s| s.as_str()),
        )
    }

    fn parse_from_file(file: &File) -> Result<Self> {
        let reader = BufReader::new(file);
        Self::parse_from_reader(reader)
    }

    fn parse_from_path(path: &PathBuf) -> Result<Self> {
        ensure!(
            path.exists(),
            format!("File doesn't exist at path: {}", path.to_str().unwrap())
        );
        let file = File::open(path)?;
        Self::parse_from_file(&file)
    }
}
