#!/usr/bin/env bash
# Esercizio 6, fase 4: invio dei job di strong scaling e raccolta dei risultati.
#
#   bash scaling.sh nodo      # 1 nodo: sequenziale (1 run) e denoise_mpi con 1, 2, 4, 8, 16 rank
#   bash scaling.sh nodi      # 2, 4, 8 nodi da 16 rank (32, 64, 128 rank), un job per numero di nodi
#   bash scaling.sh collect   # quando squeue e' vuoto: tutti i RUN, sacct e controllo SHA256
set -uo pipefail
cd "$(dirname "$0")"
[ -f images/large/noisy.pgm ] || { echo "Manca images/large/noisy.pgm (link alla cartella del corso)" >&2; exit 1; }
for f in denoise_serial denoise_mpi scaling_job.sh; do
    [ -e "$f" ] || { echo "Manca $f in $(pwd)" >&2; exit 1; }
done
SACCT_FMT=JobID,JobName%14,NodeList%24,NNodes,NTasks,AllocCPUS,Elapsed,State,ExitCode
mkdir -p scaling_logs

submit() {  # submit <nodi> <lista di rank> [serial] [time]
    local id
    id=$(sbatch --parsable --nodes="$1" --ntasks-per-node=16 --time="${4:-01:00:00}" scaling_job.sh "$2" "${3:-}") || return 1
    echo "${id%%;*}" >> scaling_logs/jobids
    echo "Inviato job ${id%%;*}: $1 nodo/i, rank: $2 ${3:-}"
}

case "${1:-}" in
nodo)
    submit 1 "1 2 4 8 16" serial 01:00:00 ;;
nodi)
    submit 2 "32" "" 00:20:00
    submit 4 "64" "" 00:20:00
    submit 8 "128" "" 00:20:00 ;;
collect)
    log=scaling_logs/collect_$(date +%Y%m%d_%H%M%S).txt
    {
        echo "========== squeue"; squeue -u "${USER:-$(id -un)}"
        for id in $(cat scaling_logs/jobids 2>/dev/null); do
            echo "========== job $id: sacct"; sacct -j "$id" --format=$SACCT_FMT
            echo "========== job $id: output"; cat "es06_scaling.$id.out" 2>/dev/null
            echo "========== job $id: errori del job"
            cat "es06_scaling.$id.err" 2>/dev/null
        done
        echo "========== tutti i RUN"
        grep -h '^RUN' es06_scaling.*.out 2>/dev/null
        echo "========== maschere di cpu-bind della ripetizione 1 (da srun --cpu-bind=verbose)"
        for f in scaling_out/*-r1.err; do echo "--- $f"; grep -h 'cpu-bind' "$f" | head -20; done
        echo "========== SHA256 della ripetizione 1 (devono essere tutti uguali)"
        grep -h '^RUN' es06_scaling.*.out 2>/dev/null | grep 'rep=1' | sed 's/.*sha256=//' | sort | uniq -c
        echo "========== sorgenti"
        sha256sum denoise_serial.c denoise_mpi.c pgm_io.h scaling_job.sh scaling.sh
    } > "$log" 2>&1
    echo "Log: $log"; tail -n 25 "$log" ;;
*)
    echo "Uso: bash scaling.sh nodo | nodi | collect" >&2; exit 1 ;;
esac
