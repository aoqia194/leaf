import argparse
import shutil
from pathlib import Path

from loguru import logger

from leaf import downloader, generator, util
from leaf.constants import INDEXES_PATH, MANIFESTS_PATH, OUT_PATH
from leaf.models import SteamInfo


def main():
    """Main EOP"""

    args, other_args = parse_args()

    if args.task == "generate":
        run_generator(args)
    elif args.task == "download":
        run_downloader(args, other_args)


def parse_args():
    """
    Parses commandline args and returns the object
    """

    cli = argparse.ArgumentParser(
        prog="leaf-generator",
        description="Handles the game manifests based on parsing game files and Steam info",
    )

    subparsers = cli.add_subparsers(dest="task", required=True)

    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--manifests-file", required=True)
    # generate_parser.add_argument("--output-path")

    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("--manifests-file", required=True)
    download_parser.add_argument("--output-path")

    return cli.parse_known_args()


def run_generator(args: argparse.Namespace):
    manifests_file = Path(args.manifests_file)
    # output_path = util.get_path(args.output_path, default=OUT_PATH)

    if not OUT_PATH.exists():
        logger.debug("Creating output path because it doesn't exist")
        OUT_PATH.mkdir(parents=True, exist_ok=True)

    if MANIFESTS_PATH.exists():
        logger.warning("Found previously-created files in generated. Removing all of them")
        shutil.rmtree(MANIFESTS_PATH)

    if INDEXES_PATH.exists():
        logger.warning("Found previously-created files in indexes. Removing all of them")
        shutil.rmtree(INDEXES_PATH)

    MANIFESTS_PATH.mkdir(parents=True, exist_ok=True)
    INDEXES_PATH.mkdir(parents=True, exist_ok=True)

    with open(manifests_file, "r", encoding="utf-8") as f:
        for line in f:
            # Skip commented lines for testing
            if line.startswith("//"):
                continue

            data = line.split(":")
            steam_info = SteamInfo(
                data[0].strip(),
                data[1].strip(),
                data[2].strip(),
                (data[3] if len(data) > 3 else "public").strip(),
            )

            logger.trace("Parsed manifest entry with info:\n\t{}", steam_info.to_json())
            generator.generate_manifests(steam_info)


def run_downloader(args: argparse.Namespace, other_args: list[str]):
    manifests_file: Path = Path(args.manifests_file.strip())

    default = Path(".")
    output_path = util.get_path(args.output_path, default=default)

    if output_path == default:
        logger.warning("Found no output path, using default (cwd)")

    try:
        with open(manifests_file, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(":")
                app_id = parts[0]
                depot_id = parts[1]
                manifest_id = parts[2]
                branch = parts[3].strip() if len(parts) >= 4 else None

                output_path = util.format_path(output_path, manifest_id)

                downloader.download(
                    app_id,
                    depot_id,
                    manifest_id,
                    branch=branch,
                    output_path=output_path,
                    other_args=other_args,
                )
    except FileNotFoundError as e:
        logger.error(f"Error: File {e.filename} not found.")


if __name__ == "__main__":
    main()
