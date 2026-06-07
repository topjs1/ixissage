#!/usr/bin/env python3
"""Download the ixissage source dataset without overwriting raw data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


DATASET_URL = (
    "https://huggingface.co/datasets/meal-bbang/Korean_message/"
    "resolve/main/lgaidataset.csv"
)
DEFAULT_OUTPUT = Path("data/raw/lgaidataset.csv")
CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_metadata(path: Path, source_url: str) -> None:
    metadata_path = path.with_name(f"{path.stem}.metadata.json")
    if metadata_path.exists():
        print(f"Metadata already exists; not overwriting: {metadata_path}")
        return

    metadata = {
        "source_url": source_url,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "note": "Raw dataset file. Do not overwrite.",
    }

    with metadata_path.open("x", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Wrote metadata: {metadata_path}")


def download_dataset(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        print(f"Raw dataset already exists; not overwriting: {output}")
        print(f"Bytes: {output.stat().st_size}")
        print(f"SHA256: {sha256_file(output)}")
        write_metadata(output, url)
        return

    temp_path = output.with_name(f"{output.name}.tmp")
    if temp_path.exists():
        temp_path.unlink()

    request = Request(url, headers={"User-Agent": "ixissage-dataset-downloader/1.0"})

    print(f"Downloading: {url}")
    print(f"Destination: {output}")
    with urlopen(request, timeout=60) as response, temp_path.open("wb") as file:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            file.write(chunk)

    if output.exists():
        temp_path.unlink(missing_ok=True)
        raise FileExistsError(f"Refusing to overwrite raw dataset: {output}")

    os.replace(temp_path, output)
    print(f"Downloaded raw dataset: {output}")
    print(f"Bytes: {output.stat().st_size}")
    print(f"SHA256: {sha256_file(output)}")
    write_metadata(output, url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download meal-bbang/Korean_message into data/raw without overwriting."
    )
    parser.add_argument(
        "--url",
        default=DATASET_URL,
        help="Dataset CSV URL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Raw CSV output path. Existing files are never overwritten.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    download_dataset(args.url, args.output)


if __name__ == "__main__":
    main()

