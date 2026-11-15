#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <mpi.h>
#include <omp.h>

/* Write the CPUs in mask as a compact list, for example "0-3,8,10-11". */
static void format_cpu_set(const cpu_set_t *mask, char *buffer, size_t size)
{
    size_t used = 0;

    buffer[0] = '\0';
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
        if (!CPU_ISSET(cpu, mask))
            continue;

        int last = cpu;
        while (last + 1 < CPU_SETSIZE && CPU_ISSET(last + 1, mask))
            ++last;

        const char *separator = used > 0 ? "," : "";
        int written = (last == cpu)
            ? snprintf(buffer + used, size - used, "%s%d", separator, cpu)
            : snprintf(buffer + used, size - used, "%s%d-%d", separator, cpu, last);
        if (written < 0 || (size_t)written >= size - used)
            break;  /* buffer full: the list is truncated */

        used += written;
        cpu = last;
    }
}

int main(int argc, char *argv[])
{
    int rank, ranks, name_length;
    char processor_name[MPI_MAX_PROCESSOR_NAME];

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);
    MPI_Get_processor_name(processor_name, &name_length);

    #pragma omp parallel
    {
        int thread = omp_get_thread_num();
        int threads = omp_get_num_threads();
        cpu_set_t mask;
        char cpus[1024];

        CPU_ZERO(&mask);
        if (sched_getaffinity(0, sizeof mask, &mask) == 0)
            format_cpu_set(&mask, cpus, sizeof cpus);
        else
            snprintf(cpus, sizeof cpus, "unknown");

        printf("Hello from thread %d/%d from rank %d/%d on %s (core affinity = %s)\n",
               thread, threads, rank, ranks, processor_name, cpus);
    }

    MPI_Finalize();
    return 0;
}
