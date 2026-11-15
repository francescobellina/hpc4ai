#!/bin/bash
#SBATCH --job-name=hello_openmp
#SBATCH --partition=lab4
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --time=5:00
#SBATCH --output=%x.%j.out

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun ./hello_shared_world
