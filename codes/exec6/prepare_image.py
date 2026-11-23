"""Create a clean synthetic image and a reproducibly corrupted copy (P2 PGM)."""

import argparse
from pathlib import Path

import numpy as np


def write_pgm(path, image):
    values = np.rint(255 * np.clip(image, 0, 1)).astype(np.uint8)
    with path.open("w", encoding="ascii") as stream:
        stream.write(f"P2\n{values.shape[1]} {values.shape[0]}\n255\n")
        np.savetxt(stream, values, fmt="%d")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--sigma", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--output", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.height < 1 or args.width < 1:
        parser.error("image dimensions must be positive")
    if not np.isfinite(args.sigma) or args.sigma < 0:
        parser.error("sigma must be finite and non-negative")
    args.output.mkdir(parents=True, exist_ok=True)

    y, x = np.mgrid[0:args.height, 0:args.width]
    x = (x + 0.5) / args.width
    y = (y + 0.5) / args.height
    clean = 0.15 + 0.15 * x
    clean[(x > 0.12) & (x < 0.42) & (y > 0.15) & (y < 0.75)] = 0.75
    clean[(x - 0.70) ** 2 + (y - 0.45) ** 2 < 0.18 ** 2] = 0.90
    clean[(x > 0.50) & (x < 0.90) & (y > 0.80) & (y < 0.86)] = 0.50
    noise = np.random.default_rng(args.seed).normal(0, args.sigma, clean.shape)
    write_pgm(args.output / "clean.pgm", clean)
    write_pgm(args.output / "noisy.pgm", clean + noise)
    print(f"Created {args.width} x {args.height} images in {args.output}")


if __name__ == "__main__":
    main()
