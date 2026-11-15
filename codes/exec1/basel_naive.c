#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(int argc, char **argv)
{
    (void)argc;
    long N = atol(argv[1]);
    int reverse = atoi(argv[2]);
    int single = atoi(argv[3]);
    double exact = M_PI * M_PI / 6.0;

    if (single) {
        float sum = 0.0f;
        if (reverse)
            for (long n = N; n >= 1; --n) sum += 1.0f / ((float)n * (float)n);
        else
            for (long n = 1; n <= N; ++n) sum += 1.0f / ((float)n * (float)n);
        printf("%ld %d %.9f %.6e\n", N, reverse, (double)sum,
               fabs((double)sum - exact));
    } else {
        double sum = 0.0;
        if (reverse)
            for (long n = N; n >= 1; --n) sum += 1.0 / ((double)n * (double)n);
        else
            for (long n = 1; n <= N; ++n) sum += 1.0 / ((double)n * (double)n);
        printf("%ld %d %.17e %.6e\n", N, reverse, sum, fabs(sum - exact));
    }
    return 0;
}
