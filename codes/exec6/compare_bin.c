/* Esercizio 6: differenza massima fra due file .bin di double (uscite di denoise_*).
       ./compare_bin a.bin b.bin
   Stampa il numero di valori e max |a - b|; esce con 1 se le dimensioni differiscono. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static double *load(const char *path, size_t *n)
{
    FILE *s = fopen(path, "rb");
    if (!s) { perror(path); exit(2); }
    fseek(s, 0, SEEK_END);
    long bytes = ftell(s);
    rewind(s);
    *n = (size_t)bytes / sizeof(double);
    double *v = malloc(*n * sizeof(*v));
    if (!v || fread(v, sizeof(*v), *n, s) != *n) { fprintf(stderr, "%s: lettura fallita\n", path); exit(2); }
    fclose(s);
    return v;
}

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "Uso: %s a.bin b.bin\n", argv[0]); return 2; }
    size_t na, nb;
    double *a = load(argv[1], &na), *b = load(argv[2], &nb);
    if (na != nb) { printf("DIMENSIONI DIVERSE: %zu e %zu valori\n", na, nb); return 1; }
    double worst = 0.0;
    for (size_t i = 0; i < na; ++i)
        worst = fmax(worst, fabs(a[i] - b[i]));
    printf("valori: %zu; max |differenza|: %.3e%s\n", na, worst, worst < 1e-12 ? " (< 1e-12)" : " (OLTRE 1e-12)");
    free(a); free(b);
    return 0;
}
