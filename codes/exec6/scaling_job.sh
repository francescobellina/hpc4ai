#!/usr/bin/bash
#SBATCH --job-name=es06_scaling
#SBATCH --output=%x.%j.out
#SBATCH --error=%x.%j.err
#SBATCH --partition=wilson
#SBATCH --constraint=sandy_bridge
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --hint=nomultithread
#SBATCH --time=01:00:00
#
# Esercizio 6, strong scaling di denoise_mpi: immagine large (8192 x 8192), lambda = 1,
# 200 iterazioni, tolleranza 0 (lavoro fisso: niente arresto anticipato, ma la
# MPI_Allreduce resta a ogni iterazione). Un rank per core fisico.
# Si invia con scaling.sh, che sceglie nodi e numeri di rank:
#   sbatch --nodes=N --ntasks-per-node=16 scaling_job.sh "<lista di rank>" [serial]
# Ogni run stampa il tempo della fase iterativa (massimo sui rank). La ripetizione 1 di
# ogni configurazione scrive anche il .bin, ne calcola lo SHA256 e lo cancella: il
# confronto bit per bit fra configurazioni si fa poi in collect, senza tenere su disco
# file da 512 MB. La PGM di uscita va su /dev/null: serve solo il .bin.
set -uo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"
module load GCC/13.2.0 OpenMPI/4.1.6 2>/dev/null
RANKS=${1:?lista di rank}
SERIAL=${2:-}
IN=${IN:-images/large/noisy.pgm}
LAMBDA=1
STEPS=${STEPS:-200}
REPS=${REPS:-3}
RUNNER=${RUNNER:-srun}           # sul Mac, per una prova: RUNNER=mpirun
OUT=scaling_out
mkdir -p "$OUT"

echo "Job: ${SLURM_JOB_ID:-locale}; nodi: ${SLURM_JOB_NODELIST:-?} (${SLURM_NNODES:-1}); task per nodo: ${SLURM_NTASKS_PER_NODE:-?}"
echo "Input: $IN; lambda: $LAMBDA; iterazioni: $STEPS; tolleranza: 0; ripetizioni: $REPS"
module list 2>&1 | grep -v '^$'
mpicc --version | head -1
if [ "$RUNNER" = srun ]; then
    echo "--- nodi e core"
    srun --ntasks-per-node=1 bash -c 'echo "$(hostname): $(lscpu | grep -m1 "Model name" | sed "s/.*: *//"), $(nproc) CPU logiche"'
fi

launch() {  # launch <rank> <programma e argomenti...>
    local p=$1
    shift
    if [ "$RUNNER" = srun ]; then
        srun --ntasks="$p" --cpu-bind=verbose,cores "$@"
    else
        mpirun --oversubscribe -n "$p" "$@"
    fi
}

one() {  # one <etichetta> <rank> <ripetizione> <programma>
    local tag=$1 p=$2 r=$3 prog=$4 bin=""
    [ "$r" = 1 ] && bin="$OUT/$tag.bin"
    local t0 t1 txt
    t0=$(date +%s.%N)
    if [ "$prog" = serial ]; then
        txt=$(launch 1 ./denoise_serial "$IN" /dev/null "$LAMBDA" "$STEPS" 0 $bin 2>"$OUT/$tag-r$r.err")
    else
        txt=$(launch "$p" ./denoise_mpi "$IN" /dev/null "$LAMBDA" "$STEPS" 0 $bin 2>"$OUT/$tag-r$r.err")
    fi
    t1=$(date +%s.%N)
    local sec it hash="-"
    sec=$(sed -n 's/.*iteration seconds: \([0-9.]*\).*/\1/p' <<<"$txt")
    it=$(sed -n 's/.*iterations: \([0-9]*\);.*/\1/p' <<<"$txt")
    if [ -n "$bin" ] && [ -f "$bin" ]; then
        hash=$(sha256sum "$bin" | cut -c1-16)
        rm -f "$bin"
    fi
    printf 'RUN %-7s P=%-4s N=%-2s rep=%s iter=%-4s iteration_seconds=%-12s total_seconds=%.1f sha256=%s\n' \
        "$tag" "$p" "${SLURM_NNODES:-1}" "$r" "${it:-ERR}" "${sec:-ERR}" "$(awk -v a="$t0" -v b="$t1" 'BEGIN{print b - a}')" "$hash"
}

if [ -n "$SERIAL" ]; then
    one serial 1 1 serial
fi
for p in $RANKS; do
    for r in $(seq 1 "$REPS"); do
        one "P$p" "$p" "$r" mpi
    done
done
echo "--- fine: $(date)"
