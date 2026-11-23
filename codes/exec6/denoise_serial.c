/* Sequential starting point for the image-denoising MPI exercise. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "pgm_io.h"

static double wall_time(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return now.tv_sec + 1e-9 * now.tv_nsec;
}

/* f has only owned rows. current and next have an extra row at each end.
   first_row identifies the strip in the global image; in serial it is zero.
   Only existing image neighbours contribute, even at the global boundary. */
static double jacobi_step(const double *f, const double *current, double *next,
                          int rows, int width, int first_row, int height,
                          double lambda)
{
    double change = 0.0;
    for (int i = 1; i <= rows; ++i) {
        int global_row = first_row + i - 1;
        for (int j = 0; j < width; ++j) {
            size_t k = (size_t)i * width + j;
            double neighbours = 0.0;
            int count = 0;
            if (global_row > 0) {
                neighbours += current[k - width];
                ++count;
            }
            if (global_row + 1 < height) {
                neighbours += current[k + width];
                ++count;
            }
            if (j > 0) {
                neighbours += current[k - 1];
                ++count;
            }
            if (j + 1 < width) {
                neighbours += current[k + 1];
                ++count;
            }
            next[k] = (f[(size_t)(i - 1) * width + j] + lambda * neighbours)
                      / (1.0 + lambda * count);
            change = fmax(change, fabs(next[k] - current[k]));
        }
    }
    return change;
}

int main(int argc, char **argv)
{
    if (argc != 6 && argc != 7) {
        fprintf(stderr, "Usage: %s input.pgm output.pgm lambda steps tolerance"
                        " [output.bin]\n", argv[0]);
        return EXIT_FAILURE;
    }

    /* Parse parameters once, outside the calculation. */
    char *end;
    errno = 0;
    double lambda = strtod(argv[3], &end);
    if (errno || end == argv[3] || *end || !isfinite(lambda) ||
        lambda <= 0 || lambda > 1e6) {
        fprintf(stderr, "Require 0 < lambda <= 1e6\n");
        return EXIT_FAILURE;
    }
    errno = 0;
    long steps = strtol(argv[4], &end, 10);
    if (errno || end == argv[4] || *end || steps < 1 || steps > INT_MAX) {
        fprintf(stderr, "Require a positive integer iteration limit <= INT_MAX\n");
        return EXIT_FAILURE;
    }
    errno = 0;
    double tolerance = strtod(argv[5], &end);
    if (errno || end == argv[5] || *end || !isfinite(tolerance) || tolerance < 0) {
        fprintf(stderr, "Require a finite, non-negative tolerance\n");
        return EXIT_FAILURE;
    }

    int height, width;
    double *f = pgm_read(argv[1], &height, &width);
    if (!f) {
        fprintf(stderr, "Cannot read input P2 image\n");
        return EXIT_FAILURE;
    }
    size_t pixels = (size_t)height * width;
    /* This limit also keeps the traditional MPI counts usable later. */
    if (pixels > INT_MAX) {
        fprintf(stderr, "Require height * width <= INT_MAX\n");
        free(f);
        return EXIT_FAILURE;
    }
    size_t padded = ((size_t)height + 2) * width;
    double *current = calloc(padded, sizeof(*current));
    double *next = calloc(padded, sizeof(*next));
    if (!current || !next) {
        fprintf(stderr, "Allocation failed\n");
        free(f); free(current); free(next);
        return EXIT_FAILURE;
    }
    /* Rows 1..height contain the image; rows 0 and height+1 are unused here. */
    memcpy(current + width, f, pixels * sizeof(*f));

    int completed = 0;
    double change = 0.0;
    double start = wall_time();
    while (completed < steps) {
        change = jacobi_step(f, current, next, height, width, 0, height, lambda);
        double *temporary = current;
        current = next;
        next = temporary;
        ++completed;
        /* A zero tolerance disables early stopping. */
        if (change < tolerance)
            break;
    }
    double elapsed = wall_time() - start;

    /* Write images after timing. The optional binary output retains doubles. */
    int ok = pgm_write(argv[2], current + width, height, width);
    if (argc == 7) {
        FILE *stream = fopen(argv[6], "wb");
        if (!stream) {
            ok = 0;
        } else {
            if (fwrite(current + width, sizeof(*current), pixels, stream) != pixels)
                ok = 0;
            if (fclose(stream) != 0)
                ok = 0;
        }
    }
    printf("Image: %d x %d; iterations: %d; max change: %.12g\n",
           height, width, completed, change);
    printf("Stop: %s; iteration seconds: %.9f\n",
           change < tolerance ? "tolerance" : "iteration limit", elapsed);
    if (!ok)
        fprintf(stderr, "Cannot write output\n");
    free(f); free(current); free(next);
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
