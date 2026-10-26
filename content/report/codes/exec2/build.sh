#!/bin/bash
set -euo pipefail

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

gcc   -Wall -Wextra -O2 -fopenmp -o hello_shared_world   hello_shared_world.c
mpicc -Wall -Wextra -O2 -fopenmp -o hello_parallel_world hello_parallel_world.c

ls -l hello_shared_world hello_parallel_world
