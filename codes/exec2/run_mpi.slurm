#!/bin/bash
#SBATCH --job-name=hello_mpi
#SBATCH --partition=lab4
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --time=5:00
#SBATCH --output=%x.%j.out

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

export OMP_NUM_THREADS=1
srun ./hello_parallel_world
