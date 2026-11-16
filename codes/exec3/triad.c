/* Banda di memoria con il kernel "triad" di STREAM: a[i] = b[i] + s * c[i].
   Tre array da N double (molto più grandi della cache L3); per ogni numero di
   thread (OMP_NUM_THREADS) si tiene il migliore di REPS ripetizioni.
   Byte contati: 3 * 8 * N per ripetizione (2 letture + 1 scrittura), come STREAM:
   il traffico reale può essere maggiore per la write-allocate. */
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#define N 40000000L   /* 320 MB per array */
#define REPS 10

int main(void)
{
    double *a = malloc(N * sizeof *a), *b = malloc(N * sizeof *b), *c = malloc(N * sizeof *c);
    if (!a || !b || !c) { fprintf(stderr, "malloc fallita\n"); return 1; }

    /* Inizializzazione parallela con lo stesso schedule del kernel (first touch). */
    #pragma omp parallel for schedule(static)
    for (long i = 0; i < N; ++i) { a[i] = 0.0; b[i] = 1.0; c[i] = 2.0; }

    double best = 1e30, s = 3.0;
    for (int r = 0; r < REPS; ++r) {
        double t = omp_get_wtime();
        #pragma omp parallel for schedule(static)
        for (long i = 0; i < N; ++i) a[i] = b[i] + s * c[i];
        t = omp_get_wtime() - t;
        if (t < best) best = t;
    }
    /* Controllo: a[i] = 1 + 3 * 2 = 7 ovunque. */
    for (long i = 0; i < N; i += N / 7)
        if (a[i] != 7.0) { fprintf(stderr, "risultato errato a[%ld] = %g\n", i, a[i]); return 1; }

    printf("triad: thread = %2d  tempo migliore = %.4f s  banda = %.2f GB/s\n",
           omp_get_max_threads(), best, 3.0 * 8.0 * N / best / 1e9);
    free(a); free(b); free(c);
    return 0;
}
