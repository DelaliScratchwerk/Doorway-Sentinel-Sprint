"""Explicit, checksum-verified model download. Never runs during hub startup."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile


REVISION = "bb17b6c3eef36d80be441ae8e5339be66e8e3b7a"
SOURCE = f"https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/{REVISION}/"
FILES = {
    "deploy.prototxt": "2d180f723b3109e21f8287f6b3c691390d07b60eed998327cd3259ffa0e50608",
    "mobilenet_iter_73000.caffemodel": "52eed8be80522c152a17fb56740de705b79881bde1a167e0e747310523685fc7",
    "LICENSE": "5de433821cfe672af2fca73c3005f48af16121c95f6a11e1031b07807ea59905",
}


def verify_file(path, expected):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f"Checksum mismatch: {path}. Run python -m hub.models to restore trusted files.")


def verify_models(directory):
    for name, digest in FILES.items():
        path = Path(directory) / name
        if not path.is_file():
            raise ValueError("Model files missing; run python -m hub.models to download them explicitly.")
        verify_file(path, digest)


def download_models(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        target = directory / name
        if target.is_file():
            try:
                verify_file(target, digest)
                continue
            except ValueError:
                pass
        fd, temporary = tempfile.mkstemp(prefix=".download-", dir=directory)
        os.close(fd)
        try:
            # System curl uses the system trust store on macOS. Do not disable TLS
            # verification to work around Python.org's missing CA configuration.
            subprocess.run([
                "curl", "--fail", "--location", "--silent", "--show-error",
                "--proto", "=https", "--proto-redir", "=https", "--max-time", "120",
                "--max-filesize", "32000000", "--output", temporary, SOURCE + name,
            ], check=True)
            verify_file(temporary, digest)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", default="models")
    args = parser.parse_args(argv)
    try:
        download_models(args.models_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Model download failed: {exc}\n")
    print(f"MobileNet-SSD files verified in {args.models_dir}")


if __name__ == "__main__":
    main()
