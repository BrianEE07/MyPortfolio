from __future__ import annotations

import shutil
import struct
import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIRECTORY = REPOSITORY_ROOT / "portfolio_app" / "static"
SOURCE_ICON = STATIC_DIRECTORY / "icon-source.png"


PNG_OUTPUTS = (
    (512, "favicon.png"),
    (192, "favicon-192.png"),
    (180, "apple-touch-icon.png"),
    (64, "favicon-64.png"),
    (32, "favicon-32.png"),
    (16, "favicon-16.png"),
)


def _resize_with_sips(source: Path, destination: Path, size: int):
    subprocess.run(
        ["sips", "-z", str(size), str(size), str(source), "--out", str(destination)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _write_ico(path: Path, png_paths: list[tuple[int, Path]]):
    entries = []
    data_blocks = []
    offset = 6 + len(png_paths) * 16
    for size, png_path in png_paths:
        data = png_path.read_bytes()
        entries.append(
            struct.pack(
                "<BBBBHHII",
                size if size < 256 else 0,
                size if size < 256 else 0,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        data_blocks.append(data)
        offset += len(data)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(png_paths)) + b"".join(entries) + b"".join(data_blocks))


def main():
    if not SOURCE_ICON.exists():
        raise FileNotFoundError(f"Missing source icon: {SOURCE_ICON}")
    if shutil.which("sips") is None:
        raise RuntimeError("This icon generator requires macOS `sips` for PNG resizing.")

    STATIC_DIRECTORY.mkdir(parents=True, exist_ok=True)
    outputs_by_size = {}
    for size, name in PNG_OUTPUTS:
        destination = STATIC_DIRECTORY / name
        _resize_with_sips(SOURCE_ICON, destination, size)
        outputs_by_size[size] = destination

    _write_ico(
        STATIC_DIRECTORY / "favicon.ico",
        [(16, outputs_by_size[16]), (32, outputs_by_size[32]), (64, outputs_by_size[64])],
    )


if __name__ == "__main__":
    main()
