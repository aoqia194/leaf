#![allow(dead_code)]

mod constants;
mod generator;
mod models;
mod parser;
mod tests;
mod utils;

use anyhow::{Context, Result, ensure};
use clap::{Parser, arg, command};
use std::path::PathBuf;
use tracing::{Level, info};

#[derive(Parser)]
#[command(version, about, long_about = None)]
struct Cli {
    #[arg(short, long)]
    verbose: bool,
    #[arg(short, long)]
    force: bool,
    #[arg(short, long, value_name = "DIR")]
    depots_dir: PathBuf,
    #[arg(short, long, value_name = "DIR")]
    output_dir: PathBuf,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    utils::setup_logger(if cli.verbose {
        Level::TRACE
    } else {
        Level::INFO
    })
    .context("Failed to setup the logger")?;

    ensure!(cli.depots_dir.exists(), "Depots directory doesn't exist");
    ensure!(cli.output_dir.exists(), "Output directory doesn't exist");

    info!("Revving up the fryers...");
    generator::generate_all(&cli).context("Failed to generate manifests")?;
    info!("Completed! Thanks for playing.");

    Ok(())
}
