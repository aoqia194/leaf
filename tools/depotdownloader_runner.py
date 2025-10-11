import os
import subprocess
import sys


def main():
    if sys.argv[1] is None:
        print("No manifest file found")
        exit(1)
    
    if sys.argv[2] is None:
        print("Found no output path, using default (cwd)")

    steam_username = os.environ["DEPOTDOWNLOADER_USERNAME"]

    try:
        with open(sys.argv[1].strip(), "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(":")
                appid = parts[0]
                depotid = parts[1]
                manifestid = parts[2]
                branch = parts[3] if len(parts) >= 4 else None

                argslist = [
                    "DepotDownloader",
                    f"-username {steam_username}",
                    "-remember-password",
                    "-manifest-only",
                    f"-app {appid}",
                    f"-depot {depotid}",
                    f"-manifest {manifestid}",
                ]
                if branch is not None:
                    argslist.append(f"-beta {branch}")
                if sys.argv[2] is not None:
                    argslist.append(f"-dir {sys.argv[2]}")

                try:
                    print(
                        f"[DepotDownloader] Running for:\n\tApp: {appid}\n\tDepot: {depotid}\n\tManifest: {manifestid}\n\tBranch: {branch}"
                    )
                    res = subprocess.run(" ".join(argslist), check=True, shell=True, text=True, capture_output=True)
                    print(f"[DepotDownloader] Exited with code {res.returncode}.")
                except subprocess.CalledProcessError as e:
                    print(f"[DepotDownloader] Failed to run command {" ".join(argslist)} with error: {e}")
                    print(f"[DepotDownloader] stdout: {e.stdout}")
                    if e.stderr:
                        print(f"[DepotDownloader] stderr: {e.stderr}")
                    exit(1)
    except FileNotFoundError:
        print(f"ERROR: File {FILENAME} not found.")
    except Exception as e:
        print(f"An unexpected error occured: {e}")


if __name__ == "__main__":
    main()
