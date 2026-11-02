/* Synthetic preprocessing pipeline: n observations and d features.
 * The row-major array stores feature j of observation i at data[i*d+j].
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static size_t positive_integer(const char *text)
{
    char *end;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || text[0] == '-' || end == text || *end ||
        value == 0 || value > SIZE_MAX) {
        fprintf(stderr, "Invalid positive integer: %s\n", text);
        exit(EXIT_FAILURE);
    }
    return (size_t)value;
}

static void generate_data(double *data, size_t n, size_t d)
{
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j)
            data[i*d+j] = (double)((i*17+j*13) % 1009) / 1009.0
                          + (double)(j % 11);
}

/* Population means and inverse standard deviations, one per feature.
 * Same two-pass algorithm as preprocess.c, but the loops are swapped so that
 * consecutive accesses are contiguous in the row-major array. */
static void compute_statistics(const double *data, size_t n, size_t d,
                               double *mean, double *scale)
{
    for (size_t j = 0; j < d; ++j)
        mean[j] = 0.0;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j)
            mean[j] += data[i*d+j];
    for (size_t j = 0; j < d; ++j)
        mean[j] /= (double)n;

    for (size_t j = 0; j < d; ++j)
        scale[j] = 0.0;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j) {
            double delta = data[i*d+j] - mean[j];
            scale[j] += delta * delta;
        }
    for (size_t j = 0; j < d; ++j)
        scale[j] = 1.0 / sqrt(scale[j] / (double)n + 1e-12);
}

/* Apply the supplied statistics to the working data in place. */
static void standardize(double *data, size_t n, size_t d,
                        const double *mean, const double *scale)
{
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < d; ++j)
            data[i*d+j] = (data[i*d+j] - mean[j]) * scale[j];
}

/* Evaluate a linear score with fixed weights; no model is trained. */
static void compute_scores(const double *data, size_t n, size_t d,
                           const double *weights, double *scores)
{
    for (size_t i = 0; i < n; ++i) {
        double score = 0.0;
        for (size_t j = 0; j < d; ++j)
            score += data[i*d+j] * weights[j];
        scores[i] = score;
    }
}

/* Extra checks for a small non-constant dataset; omit from timed runs. */
static void validate(const double *data, size_t n, size_t d,
                     const double *scores)
{
    double max_mean = 0.0, max_variance_error = 0.0;
    for (size_t j = 0; j < d; ++j) {
        double sum = 0.0, squared_sum = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double value = data[i*d+j];
            sum += value;
            squared_sum += value * value;
        }
        double mean = sum / (double)n;
        double error = fabs(squared_sum / (double)n - mean*mean - 1.0);
        if (!isfinite(mean) || !isfinite(error) ||
            fabs(mean) > 1e-8 || error > 1e-8) {
            fprintf(stderr, "Validation failed for feature %zu\n", j);
            exit(EXIT_FAILURE);
        }
        max_mean = fmax(max_mean, fabs(mean));
        max_variance_error = fmax(max_variance_error, error);
    }
    for (size_t i = 0; i < n; ++i) {
        double reference = 0.0;
        for (size_t j = 0; j < d; ++j)
            reference += data[i*d+j] / (double)(j+1);
        if (!isfinite(scores[i]) ||
            fabs(scores[i] - reference) > 1e-10 * (1.0 + fabs(reference))) {
            fprintf(stderr, "Score validation failed for observation %zu\n", i);
            exit(EXIT_FAILURE);
        }
    }
    printf("Validation: PASS (max |mean| %.3e; max variance error %.3e)\n",
           max_mean, max_variance_error);
}

int main(int argc, char **argv)
{
    if (argc != 4 && argc != 5) {
        fprintf(stderr, "Usage: %s observations features repeats [check]\n", argv[0]);
        return EXIT_FAILURE;
    }
    int check = argc == 5;
    if (check && strcmp(argv[4], "check") != 0) {
        fprintf(stderr, "The optional argument must be check\n");
        return EXIT_FAILURE;
    }
    size_t n = positive_integer(argv[1]);
    size_t d = positive_integer(argv[2]);
    size_t repeats = positive_integer(argv[3]);
    if (n > SIZE_MAX / sizeof(double) / d) {
        fprintf(stderr, "Requested matrix is too large\n");
        return EXIT_FAILURE;
    }
    size_t bytes = n*d*sizeof(double);
    double *original = malloc(bytes), *data = malloc(bytes);
    double *mean = malloc(d*sizeof(double)), *scale = malloc(d*sizeof(double));
    double *weights = malloc(d*sizeof(double)), *scores = malloc(n*sizeof(double));
    if (!original || !data || !mean || !scale || !weights || !scores) {
        fprintf(stderr, "Could not allocate arrays\n");
        return EXIT_FAILURE;
    }
    generate_data(original, n, d);
    for (size_t j = 0; j < d; ++j)
        weights[j] = 1.0 / (double)(j+1);

    double checksum = 0.0;
    for (size_t repeat = 0; repeat < repeats; ++repeat) {
        /* Each repetition starts from the same unstandardized input. */
        memcpy(data, original, bytes);
        compute_statistics(data, n, d, mean, scale);
        standardize(data, n, d, mean, scale);
        compute_scores(data, n, d, weights, scores);
        /* Use every score so the calculated results remain observable. */
        for (size_t i = 0; i < n; ++i)
            checksum += scores[i] * scores[i];
    }
    printf("Observations: %zu; features: %zu; repeats: %zu\n", n, d, repeats);
    printf("Checksum: %.17g\n", checksum);
    if (check)
        validate(data, n, d, scores);
    free(scores); free(weights); free(scale); free(mean);
    free(data); free(original);
    return EXIT_SUCCESS;
}
