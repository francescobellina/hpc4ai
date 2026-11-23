/* Esercizio 6 (HPC4AI): versione MPI a strisce orizzontali di denoise_serial.c.

   Stessi argomenti e stesso output del programma del corso:
       mpirun -n P ./denoise_mpi input.pgm output.pgm lambda steps tolerance [output.bin]
   jacobi_step e' copiata senza modifiche da denoise_serial.c: ogni rank la chiama
   sulla propria striscia, con first_row uguale alla sua prima riga globale.

   Schema:
   1. il rank 0 legge argomenti e immagine; dimensioni e parametri vanno a tutti con
      MPI_Bcast;
   2. le H righe si dividono in strisce contigue: i primi H % P rank hanno una riga
      in piu' (serve 1 <= P <= H); MPI_Scatterv distribuisce f;
   3. a ogni iterazione: scambio degli halo con MPI_Sendrecv (una riga per lato,
      perche' lo stencil usa solo i primi vicini), jacobi_step sulla striscia,
      MPI_Allreduce(MPI_MAX) della variazione massima, stessa decisione su tutti i rank;
   4. MPI_Gatherv raccoglie la ricostruzione sul rank 0, che scrive le immagini.
   Il tempo stampato e' quello della fase iterativa (scambi e riduzione compresi), il
   massimo sui rank, misurato con MPI_Wtime dopo una MPI_Barrier. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pgm_io.h"

/* Identica a denoise_serial.c del corso. */
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

/* Righe e prima riga globale del rank r: i primi height % size rank hanno una riga in piu'. */
static void strip(int r, int size, int height, int *rows, int *first_row)
{
    int base = height / size, extra = height % size;
    *rows = base + (r < extra ? 1 : 0);
    *first_row = r * base + (r < extra ? r : extra);
}

/* Come denoise_serial.c: restituisce un messaggio d'errore, o NULL se gli argomenti vanno bene. */
static const char *parse(int argc, char **argv, double *lambda, long *steps, double *tolerance)
{
    if (argc != 6 && argc != 7)
        return "Usage: denoise_mpi input.pgm output.pgm lambda steps tolerance [output.bin]";
    char *end;
    errno = 0;
    *lambda = strtod(argv[3], &end);
    if (errno || end == argv[3] || *end || !isfinite(*lambda) || *lambda <= 0 || *lambda > 1e6)
        return "Require 0 < lambda <= 1e6";
    errno = 0;
    *steps = strtol(argv[4], &end, 10);
    if (errno || end == argv[4] || *end || *steps < 1 || *steps > INT_MAX)
        return "Require a positive integer iteration limit <= INT_MAX";
    errno = 0;
    *tolerance = strtod(argv[5], &end);
    if (errno || end == argv[5] || *end || !isfinite(*tolerance) || *tolerance < 0)
        return "Require a finite, non-negative tolerance";
    return NULL;
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    /* 1. Solo il rank 0 legge argomenti e immagine; poi tutti ricevono dimensioni e
          parametri. ints = {ok, height, width, steps}, reals = {lambda, tolerance}. */
    int ints[4] = {0, 0, 0, 0};
    double reals[2] = {0.0, 0.0};
    double *global = NULL;
    if (rank == 0) {
        long steps = 0;
        const char *error = parse(argc, argv, &reals[0], &steps, &reals[1]);
        int height = 0, width = 0;
        if (!error && !(global = pgm_read(argv[1], &height, &width)))
            error = "Cannot read input P2 image";
        if (!error && (size_t)height * width > INT_MAX)
            error = "Require height * width <= INT_MAX";
        if (!error && size > height)
            error = "Require 1 <= number of ranks <= image height";
        if (error)
            fprintf(stderr, "%s\n", error);
        ints[0] = error == NULL;
        ints[1] = height;
        ints[2] = width;
        ints[3] = (int)steps;
    }
    MPI_Bcast(ints, 4, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(reals, 2, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    if (!ints[0]) {
        free(global);
        MPI_Finalize();
        return EXIT_FAILURE;
    }
    const int height = ints[1], width = ints[2], steps = ints[3];
    const double lambda = reals[0], tolerance = reals[1];

    /* 2. Strisce contigue; counts e displs in pixel per Scatterv e Gatherv. Il rank 0
          tiene l'immagine intera solo per leggere e scrivere; gli altri no. */
    int rows, first_row;
    strip(rank, size, height, &rows, &first_row);
    int *counts = malloc(size * sizeof(*counts)), *displs = malloc(size * sizeof(*displs));
    double *f = malloc((size_t)rows * width * sizeof(*f));
    double *current = calloc(((size_t)rows + 2) * width, sizeof(*current));
    double *next = calloc(((size_t)rows + 2) * width, sizeof(*next));
    int ok = counts && displs && f && current && next;
    int all_ok;
    MPI_Allreduce(&ok, &all_ok, 1, MPI_INT, MPI_LAND, MPI_COMM_WORLD);
    if (!all_ok) {
        if (rank == 0)
            fprintf(stderr, "Allocation failed\n");
        free(counts); free(displs); free(f); free(current); free(next); free(global);
        MPI_Finalize();
        return EXIT_FAILURE;
    }
    for (int r = 0; r < size; ++r) {
        int rr, fr;
        strip(r, size, height, &rr, &fr);
        counts[r] = rr * width;
        displs[r] = fr * width;
    }
    MPI_Scatterv(global, counts, displs, MPI_DOUBLE, f, rows * width, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    memcpy(current + width, f, (size_t)rows * width * sizeof(*f));

    /* Vicini: MPI_PROC_NULL ai bordi dell'immagine, dove lo scambio non fa nulla e
       jacobi_step non legge la riga di halo (global_row == 0 o == height - 1). */
    const int up = rank > 0 ? rank - 1 : MPI_PROC_NULL;
    const int down = rank < size - 1 ? rank + 1 : MPI_PROC_NULL;

    /* 3. Fase iterativa. */
    int completed = 0;
    double change = 0.0;
    MPI_Barrier(MPI_COMM_WORLD);
    double start = MPI_Wtime();
    while (completed < steps) {
        /* Prima riga posseduta -> halo inferiore del rank sopra; dal rank sotto -> riga rows + 1. */
        MPI_Sendrecv(current + width, width, MPI_DOUBLE, up, 0,
                     current + ((size_t)rows + 1) * width, width, MPI_DOUBLE, down, 0,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        /* Ultima riga posseduta -> halo superiore del rank sotto; dal rank sopra -> riga 0. */
        MPI_Sendrecv(current + (size_t)rows * width, width, MPI_DOUBLE, down, 1,
                     current, width, MPI_DOUBLE, up, 1,
                     MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        double local = jacobi_step(f, current, next, rows, width, first_row, height, lambda);
        MPI_Allreduce(&local, &change, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
        double *temporary = current;
        current = next;
        next = temporary;
        ++completed;
        /* change e' lo stesso su tutti i rank: la decisione e' comune. */
        if (change < tolerance)
            break;
    }
    double elapsed = MPI_Wtime() - start, slowest;
    MPI_Reduce(&elapsed, &slowest, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    /* 4. Raccolta e scrittura sul rank 0, fuori dal tempo misurato. */
    MPI_Gatherv(current + width, rows * width, MPI_DOUBLE, global, counts, displs, MPI_DOUBLE,
                0, MPI_COMM_WORLD);
    int written = 1;
    if (rank == 0) {
        size_t pixels = (size_t)height * width;
        written = pgm_write(argv[2], global, height, width);
        if (argc == 7) {
            FILE *stream = fopen(argv[6], "wb");
            if (!stream) {
                written = 0;
            } else {
                if (fwrite(global, sizeof(*global), pixels, stream) != pixels)
                    written = 0;
                if (fclose(stream) != 0)
                    written = 0;
            }
        }
        int min_rows = height / size, max_rows = min_rows + (height % size ? 1 : 0);
        printf("Image: %d x %d; iterations: %d; max change: %.12g\n",
               height, width, completed, change);
        printf("Stop: %s; iteration seconds: %.9f\n",
               change < tolerance ? "tolerance" : "iteration limit", slowest);
        printf("Ranks: %d; rows per rank: %d-%d\n", size, min_rows, max_rows);
        if (!written)
            fprintf(stderr, "Cannot write output\n");
    }
    free(counts); free(displs); free(f); free(current); free(next); free(global);
    MPI_Finalize();
    return written ? EXIT_SUCCESS : EXIT_FAILURE;
}
