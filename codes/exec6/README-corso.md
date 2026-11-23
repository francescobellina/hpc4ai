# Image denoising

These are the starting files for the image-denoising MPI exercise. Begin with
the sequential solver, validate it, then adapt it to distributed-memory execution.

- `denoise_serial.c`: a sequential Jacobi solver in one C file. Its two
  reconstruction arrays include extra rows that can become MPI halos.
- `prepare_image.py`: creates `clean.pgm` and `noisy.pgm`, with NumPy as its
  only external dependency. Defaults: 1024 by 1024 pixels, noise standard
  deviation 0.12 before clipping, seed 12345.
- `pgm_io.h`: C helpers for ASCII PGM (P2) files, with comments supported in
  the input. Other PGM encodings such as binary P5 are not accepted.

## Prepared images

On WILSON, use the shared `images/small/` (17 by 19 pixels),
`images/medium/` (2048 by 2048 pixels), and `images/large/` (8192 by 8192 pixels)
directories under
`/srv/data/wilson/project/hpc4ai/exercises/image-denoising/`.
Each contains `clean.pgm` and `noisy.pgm`. All three pairs use seed 12345 and
noise standard deviation 0.30 before clipping. The small pair is for debugging;
the medium pair is for reconstruction and initial single-node scaling, and the
large pair is for the larger MPI scaling study. Read the shared inputs
directly or link the `images` directory into your working directory. Write
results elsewhere. Using these prepared inputs does not require Python.

The images are generated separately on WILSON and are ignored by Git. To
provision them, run from this exercise directory with Python and NumPy. These
commands explicitly select the stronger noise level, overriding the script's
default of 0.12:

```bash
python prepare_image.py --height 17 --width 19 --sigma 0.30 \
    --seed 12345 --output images/small
python prepare_image.py --height 2048 --width 2048 --sigma 0.30 \
    --seed 12345 --output images/medium
python prepare_image.py --height 8192 --width 8192 --sigma 0.30 \
    --seed 12345 --output images/large
chmod -R g+rX images
```

Students can use the same script in their own directories to generate custom
inputs, choosing a different output directory such as `my-images`.

## Build and run the sequential solver

Copy `denoise_serial.c` and `pgm_io.h` into your own working directory and link
the shared `images` directory. Compile with:

```bash
gcc -O2 -std=c11 -Wall -Wextra denoise_serial.c -lm -o denoise_serial
```

Within a one-core Slurm allocation, run:

```bash
srun --cpu-bind=cores ./denoise_serial images/small/noisy.pgm \
    small-serial.pgm 1 200 1e-6 small-serial.bin
srun --cpu-bind=cores ./denoise_serial images/medium/noisy.pgm \
    serial.pgm 1 200 1e-6 serial.bin
```

Arguments are input image, output image, smoothing parameter, maximum iterations,
tolerance, and an optional raw output filename. Use tolerance zero for fixed work.
The raw file contains native doubles in row-major order, without a header, for
full-precision comparisons on the same system. PGM output is rounded for viewing.
The solver prints the iteration count, maximum change, stopping reason, and
iteration time, excluding image input and output. Use the large input with
tolerance zero for the main MPI scaling study. Request sufficient memory;
4 GiB per node is a suitable starting point, including a one-rank MPI run.

`jacobi_step` reads the current iterate and fixed noisy input, writes the next
iterate, and returns the maximum change. The main loop swaps the arrays. Owned
rows occupy indices 1 through `rows`; the extra boundary rows are not read in
serial. Parameters `rows`, `first_row`, and `height` allow the same kernel to
update a local strip once MPI supplies its halos. You may instead write your own
solver with the same numerical conventions.

## Image I/O

Include `pgm_io.h` in your C source. Link with `-lm`. The interfaces are:

```c
double *pgm_read(const char *path, int *height, int *width);
int pgm_write(const char *path, const double *image, int height, int width);
```

`pgm_read` allocates a row-major array of normalized doubles, or returns
`NULL` on failure. Free the array when finished. `pgm_write` returns 1 on
success and 0 on failure. Output is rounded to 8-bit pixels for viewing;
compare solver arrays before this conversion when validating correctness.

Keep the clean image only for evaluation: the solver receives the noisy
image. On WILSON, copy these small support files to your own working directory
before generating images, compiling, or writing output.
