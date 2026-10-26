#include <stdio.h>
#include <unistd.h>
#include <omp.h>

int main(void)
{
    char hostname[256];
    gethostname(hostname, sizeof hostname);

    #pragma omp parallel
    {
        int thread = omp_get_thread_num();
        int threads = omp_get_num_threads();

        printf("Hello from thread %d/%d on %s\n", thread, threads, hostname);
    }

    return 0;
}
