Profiling and optimizing data preparation
=========================================

Starting files for the HPC4AI profiling exercise.

preprocess.c generates a reproducible synthetic dataset, calculates feature
statistics, standardizes the observations, and computes linear scores.
No external data files or libraries beyond the C standard library and libm
are required. The exercise uses GCC, GNU Time (/usr/bin/time), and perf.

Copy preprocess.c into your own working directory before compiling or editing
it. Keep the shared reference copy unchanged. Read the source and predict the
hotspot before collecting a profile.

Build
-----

gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra \
    preprocess.c -lm -o preprocess

Run on WILSON
-------------

Obtain one physical core in an interactive allocation:

salloc --nodes=1 --ntasks=1 --cpus-per-task=1 \
    --hint=nomultithread --mem=1G --time=00:15:00

Small correctness check (expect Validation: PASS):

srun --cpu-bind=cores ./preprocess 1024 32 1 check

Whole-process timing (repeat three times):

srun --cpu-bind=cores /usr/bin/time -f 'Elapsed seconds: %e' \
    ./preprocess 65536 256 5

Collect and inspect a profile:

srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g \
    -o perf-before.data ./preprocess 65536 256 5
perf report --stdio -i perf-before.data

Arguments are: observations features repeats [check]. Omit check from timed
and profiled runs, since it adds validation work. Each repetition restores
the same input before processing it. The two full-size data arrays occupy
256 MiB in total; the 1 GiB allocation also covers the remaining arrays and
process overhead. The program prints a checksum to help compare versions.

Release the allocation with exit when finished.

Assignment and worked guide
---------------------------

https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/profiling-data-preparation.html
