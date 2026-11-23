/* Minimal ASCII PGM (P2) I/O. Pixel values in memory are doubles in [0, 1]. */
#ifndef HPC4AI_PGM_IO_H
#define HPC4AI_PGM_IO_H

#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int pgm_token(FILE *stream, char *token, size_t capacity)
{
    int c;
    do {
        c = fgetc(stream);
        if (c == '#')
            while (c != '\n' && c != EOF)
                c = fgetc(stream);
    } while (c != EOF && isspace((unsigned char)c));
    if (c == EOF)
        return 0;
    size_t used = 0;
    while (c != EOF && !isspace((unsigned char)c) && c != '#') {
        if (used + 1 >= capacity)
            return 0;
        token[used++] = (char)c;
        c = fgetc(stream);
    }
    if (c == '#')
        while (c != '\n' && c != EOF)
            c = fgetc(stream);
    token[used] = '\0';
    return used != 0;
}

static int pgm_integer(FILE *stream, int *value)
{
    char token[64], *end;
    if (!pgm_token(stream, token, sizeof(token)))
        return 0;
    errno = 0;
    long parsed = strtol(token, &end, 10);
    if (errno || *end || parsed < 0 || parsed > INT_MAX)
        return 0;
    *value = (int)parsed;
    return 1;
}

/* The caller owns the returned array. NULL indicates an invalid/unreadable file. */
static inline double *pgm_read(const char *path, int *height, int *width)
{
    FILE *stream = fopen(path, "r");
    if (!stream)
        return NULL;
    char magic[64];
    int maximum;
    double *image = NULL;
    if (!pgm_token(stream, magic, sizeof(magic)) || strcmp(magic, "P2") ||
        !pgm_integer(stream, width) || !pgm_integer(stream, height) ||
        *height < 1 || *width < 1 || !pgm_integer(stream, &maximum) ||
        maximum < 1 || maximum > 65535 ||
        (size_t)*height > SIZE_MAX / sizeof(double) / (size_t)*width)
        goto fail;
    size_t pixels = (size_t)*height * (size_t)*width;
    image = malloc(pixels * sizeof(*image));
    if (!image)
        goto fail;
    for (size_t i = 0; i < pixels; ++i) {
        int value;
        if (!pgm_integer(stream, &value) || value > maximum)
            goto fail;
        image[i] = (double)value / maximum;
    }
    if (pgm_token(stream, magic, sizeof(magic)))
        goto fail;
    fclose(stream);
    return image;
fail:
    free(image);
    fclose(stream);
    return NULL;
}

/* Rounds for visualization only. Keep full precision for numerical comparisons. */
static inline int pgm_write(const char *path, const double *image,
                            int height, int width)
{
    FILE *stream = fopen(path, "w");
    if (!stream)
        return 0;
    int ok = fprintf(stream, "P2\n%d %d\n255\n", width, height) >= 0;
    for (int i = 0; i < height && ok; ++i) {
        for (int j = 0; j < width && ok; ++j) {
            double value = image[(size_t)i * width + j];
            if (!isfinite(value)) {
                ok = 0;
                break;
            }
            value = fmin(1.0, fmax(0.0, value));
            ok = fprintf(stream, "%d%c", (int)lround(255 * value),
                         j + 1 == width ? '\n' : ' ') >= 0;
        }
    }
    return fclose(stream) == 0 && ok;
}

#endif
