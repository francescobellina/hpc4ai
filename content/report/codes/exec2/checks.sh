#!/usr/bin/env bash
# Verifica completa dell'Esercitazione 2 (Parallel Hello, World!) su WILSON.
#
#   bash checks.sh all        # build + quick + submit + wait + validate
#   bash checks.sh build      # compila i due programmi
#   bash checks.sh quick      # test brevi sul nodo di login
#   bash checks.sh submit     # invia i tre job Slurm
#   bash checks.sh wait       # attende la fine dei job inviati
#   bash checks.sh validate   # controlla gli output dei job
#
# Va eseguito nella stessa cartella di hello_shared_world.c, run_*.slurm ecc.
# Si aspetta una shell bash di login (module già inizializzato).
set -uo pipefail

cd -- "$(dirname -- "$0")" || exit 1

fail=0
say()  { printf '%s\n' "$*"; }
ok()   { printf 'OK    %s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; fail=1; }
note() { printf '      %s\n' "$*"; }

load_modules() {
    type module >/dev/null 2>&1 || { bad "'module' non disponibile: apri una shell di login (bash -l)"; return 1; }
    module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core >/dev/null
    module load GCC/13.2.0 >/dev/null
    module load OpenMPI/4.1.6 >/dev/null
}

do_build() {
    command -v gcc   >/dev/null || { bad "gcc assente"; return 1; }
    command -v mpicc >/dev/null || { bad "mpicc assente"; return 1; }
    say "compilazione (gcc $(gcc -dumpversion), $(mpicc --showme:version 2>/dev/null | head -1))"
    gcc -Wall -Wextra -O2 -fopenmp -o hello_shared_world hello_shared_world.c \
        || { bad "compilazione hello_shared_world"; return 1; }
    mpicc -Wall -Wextra -O2 -fopenmp -o hello_parallel_world hello_parallel_world.c \
        || { bad "compilazione hello_parallel_world"; return 1; }
    ok "binari creati"
    ls -l hello_shared_world hello_parallel_world
}

# validate_file <file> <rank attesi P> <thread attesi T> <etichetta>
# Accetta entrambi i formati:
#   Hello from thread t/T on host
#   Hello from thread t/T from rank r/P on host (core affinity = ...)
validate_file() {
    local out=$1 P=$2 T=$3 label=$4
    if [ ! -s "$out" ]; then
        bad "$label: output assente o vuoto ($out)"
        return 1
    fi
    awk -v P="$P" -v T="$T" -v label="$label" '
        /^Hello from thread/ {
            split($4, tt, "/")
            t = tt[1] + 0
            tn = tt[2] + 0
            if ($5 == "from") { split($7, rr, "/"); r = rr[1] + 0; rn = rr[2] + 0; host = $9 }
            else               { r = 0; rn = 1; host = $6 }
            n++
            if (tn != T || rn != P) badtot = 1
            seen[r, t] = 1
            hosts[host] = 1
        }
        END {
            nodes = 0; for (h in hosts) nodes++
            status = 0
            if (n != P * T) {
                printf "FAIL  %s: %d righe, attese %d (P=%d x T=%d)\n", label, n, P * T, P, T
                status = 1
            } else {
                printf "OK    %s: %d righe = %d rank x %d thread\n", label, n, P, T
            }
            for (r = 0; r < P; r++)
                for (t = 0; t < T; t++)
                    if (!((r, t) in seen)) {
                        printf "FAIL  %s: manca rank %d thread %d\n", label, r, t
                        status = 1
                    }
            if (badtot) { printf "FAIL  %s: totale rank/thread stampato diverso da P=%d / T=%d\n", label, P, T; status = 1 }
            printf "      %s: nodi distinti = %d\n", label, nodes
            exit status
        }
    ' "$out" || fail=1
}

do_quick() {
    local t=4
    say "test brevi sul nodo di login (non sono esecuzioni di produzione)"
    OMP_NUM_THREADS=$t ./hello_shared_world > quick_openmp.out 2>&1
    validate_file quick_openmp.out 1 $t "quick OpenMP T=$t"

    OMP_NUM_THREADS=1 mpiexec -n 1 ./hello_parallel_world > quick_mpi_1x1.out 2>&1
    validate_file quick_mpi_1x1.out 1 1 "quick MPI P=1 T=1"

    OMP_NUM_THREADS=2 mpiexec -n 1 ./hello_parallel_world > quick_mpi_1x2.out 2>&1
    validate_file quick_mpi_1x2.out 1 2 "quick MPI P=1 T=2"

    OMP_NUM_THREADS=2 mpiexec -n 2 ./hello_parallel_world > quick_mpi_2x2.out 2>&1
    validate_file quick_mpi_2x2.out 2 2 "quick MPI P=2 T=2"
}

do_submit() {
    : > jobs.tsv
    local script jid
    for script in run_openmp.slurm run_mpi.slurm run_hybrid.slurm; do
        jid=$(sbatch --parsable "$script") || { bad "sbatch $script"; continue; }
        jid=${jid%%;*}
        printf '%s\t%s\n' "$script" "$jid" >> jobs.tsv
        ok "inviato $script (job $jid)"
    done
    [ -s jobs.tsv ] || return 1
    note "stato: squeue -u $USER"
}

do_wait() {
    [ -s jobs.tsv ] || { bad "nessun job registrato: esegui prima 'submit'"; return 1; }
    local ids elapsed=0
    ids=$(cut -f2 jobs.tsv | paste -sd, -)
    while [ -n "$(squeue -h -j "$ids" -o %i 2>/dev/null)" ]; do
        [ "$elapsed" -ge 900 ] && { bad "timeout 15 min: job ancora in coda ($ids)"; return 1; }
        sleep 5
        elapsed=$((elapsed + 5))
    done
    ok "tutti i job sono terminati"
}

do_validate() {
    [ -s jobs.tsv ] || { bad "nessun job registrato: esegui prima 'submit'"; return 1; }
    local script jid
    while IFS="$(printf '\t')" read -r script jid; do
        case "$script" in
            run_openmp.slurm) validate_file "hello_openmp.$jid.out" 1 4 "Slurm OpenMP (job $jid)" ;;
            run_mpi.slurm)    validate_file "hello_mpi.$jid.out"    4 1 "Slurm MPI (job $jid)" ;;
            run_hybrid.slurm) validate_file "hello_hybrid.$jid.out" 4 4 "Slurm ibrido (job $jid)" ;;
        esac
    done < jobs.tsv
    note "attese: OpenMP 4 righe, MPI 4, ibrido 16; ibrido su 2 nodi distinti"
}

case "${1:-all}" in
    build)    load_modules && do_build ;;
    quick)    load_modules && do_build && do_quick ;;
    submit)   load_modules && do_submit ;;
    wait)     do_wait ;;
    validate) do_validate ;;
    all)
        load_modules || exit 1
        do_build || exit 1
        do_quick
        do_submit
        do_wait
        do_validate
        ;;
    *) say "uso: bash checks.sh [all|build|quick|submit|wait|validate]"; exit 2 ;;
esac

if [ "$fail" -ne 0 ]; then
    say "ESITO: almeno un controllo e' fallito"
    exit 1
fi
say "ESITO: tutti i controlli superati"
