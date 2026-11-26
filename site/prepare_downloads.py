"""Build the website download directory from a tagged release. Requires Git and curl."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SITE = Path(__file__).resolve().parent
ROOT = SITE.parent


def sha256(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def build_downloads(destination, local=False):
    release = json.loads((SITE / "release-assets.json").read_text())
    tag = release["tag"]
    commit = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    if commit != release["commit"]:
        raise ValueError(f"{tag} points to {commit}, which does not match the pinned release commit.")
    if git("ls-tree", "-r", "--name-only", commit, "--", "site/dist/downloads"):
        raise ValueError("The tagged source includes generated website downloads.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".release-downloads-", dir=destination.parent) as scratch:
        stage = Path(scratch)
        checksums = {}
        for asset in release["assets"]:
            name = asset["file"]
            if Path(name).name != name or name in ("", ".", "..", "source.zip", "SHA256SUMS") or name in checksums:
                raise ValueError(f"Invalid or duplicate asset name: {name}")
            checksum = asset["sha256"]
            if not re.fullmatch("[0-9a-f]{64}", checksum):
                raise ValueError(f"Invalid SHA-256 for {name}.")
            target = stage / name
            if local:
                shutil.copyfile(ROOT / asset["localDirectory"] / name, target)
            else:
                url = f"https://github.com/{release['repository']}/releases/download/{tag}/{name}"
                subprocess.run(["curl", "--disable", "--fail", "--location", "--silent", "--show-error",
                                "--proto", "=https", "--proto-redir", "=https", "--retry", "3",
                                "--connect-timeout", "15", "--max-time", "180", "--output", str(target), url],
                               check=True)
            if sha256(target) != checksum:
                raise ValueError(f"SHA-256 mismatch for {name}. Existing downloads were left in place.")
            checksums[name] = checksum

        source = stage / "source.zip"
        slug = release["repository"].split("/")[-1]
        git("archive", "--format=zip", f"--prefix={slug}-{tag}/", "-o", str(source), commit)
        checksums[source.name] = sha256(source)
        (stage / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in checksums.items()))

        destination.mkdir(exist_ok=True)
        # The live directory is updated only after every asset has passed verification.
        for name in [*checksums, "SHA256SUMS"]:
            os.replace(stage / name, destination / name)
    print(f"Prepared website downloads for {tag} ({commit[:12]}) in {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Use the local build products, verified by digest.")
    parser.add_argument("--output", type=Path, default=SITE / "dist/downloads",
                        help="Destination directory (default: site/dist/downloads).")
    args = parser.parse_args()
    try:
        build_downloads(args.output.resolve(), local=args.local)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Could not build release downloads: {exc}")
