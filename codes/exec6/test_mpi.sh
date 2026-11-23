#!/usr/bin/env bash
# Esercizio 6: validazione di denoise_mpi contro denoise_serial, per piccoli passi.
#
#   bash test_mpi.sh uno     # 1 rank
#   bash test_mpi.sh nodo    # piu' rank sullo stesso nodo (2, 3, 4, 8, 16; una riga per rank)
#   bash test_mpi.sh nodi    # piu' nodi (17 rank su 2 nodi: una riga per rank su small)
#
# Lanciatore: variabile LAUNCH, seguita dal numero di rank. Default per WILSON:
#   LAUNCH="srun -p wilson --constraint=sandy_bridge --cpu-bind=cores -n"
# con NODES1="-N 1" (uno, nodo) e NODES2="-N 2" (nodi). Sul Mac, un nodo solo:
#   LAUNCH="mpirun --oversubscribe -n" NODES1="" NODES2="" bash test_mpi.sh nodo
# Ogni caso confronta il .bin con quello sequenziale (soglia 1e-12) e il numero di
# iterazioni e la ragione d'arresto stampati.
set -uo pipefail
cd "$(dirname "$0")"
LAUNCH=${LAUNCH:-"srun -p wilson --constraint=sandy_bridge --cpu-bind=cores -n"}
NODES1=${NODES1-"-N 1"}
NODES2=${NODES2-"-N 2"}
mkdir -p out

ref() {  # ref <nome> <input> <lambda> <steps> <tol>: uscita sequenziale di riferimento
    [ -f "out/$1-serial.bin" ] || ./denoise_serial "$2" "out/$1-serial.pgm" "$3" "$4" "$5" "out/$1-serial.bin" > "out/$1-serial.txt"
}

check() {  # check <nome> <input> <lambda> <steps> <tol> <rank> [opzioni del lanciatore]
    local name=$1 input=$2 lam=$3 steps=$4 tol=$5 p=$6
    shift 6
    ref "$name" "$input" "$lam" "$steps" "$tol"
    local tag="$name-p$p"
    $LAUNCH "$p" "$@" ./denoise_mpi "$input" "out/$tag.pgm" "$lam" "$steps" "$tol" "out/$tag.bin" > "out/$tag.txt" 2>&1
    local it_s it_m
    it_s=$(sed -n 's/.*iterations: \([0-9]*\);.*/\1/p; s/^Stop: \([a-z ]*\);.*/\1/p' "out/$name-serial.txt" | paste -sd' ' -)
    it_m=$(sed -n 's/.*iterations: \([0-9]*\);.*/\1/p; s/^Stop: \([a-z ]*\);.*/\1/p' "out/$tag.txt" | paste -sd' ' -)
    printf '%-14s P=%-3s lambda=%-4s steps=%-4s tol=%-6s | seriale: %-22s | MPI: %-22s %s | %s\n' \
        "$name" "$p" "$lam" "$steps" "$tol" "$it_s" "$it_m" "$([ "$it_s" = "$it_m" ] && echo uguali || echo DIVERSI)" \
        "$(./compare_bin "out/$name-serial.bin" "out/$tag.bin" 2>&1)"
    grep -h '^Ranks:' "out/$tag.txt" | sed 's/^/    /'
}

prepare() {
    printf 'P2\n2 2\n255\n0 255\n255 0\n' > out/t2x2.pgm
    { printf 'P2\n19 8\n255\n'; sed -n '4,11p' images/small/noisy.pgm; } > out/small8.pgm   # prime 8 righe di small
}

prepare
case "${1:-}" in
uno)
    for c in "t2x2 out/t2x2.pgm 1 200 1e-6" "small images/small/noisy.pgm 1 200 1e-6" \
             "small-fisso images/small/noisy.pgm 1 200 0" "medium images/medium/noisy.pgm 1 200 1e-6"; do
        set -- $c; check "$1" "$2" "$3" "$4" "$5" 1 ${NODES1}
    done ;;
nodo)
    check t2x2 out/t2x2.pgm 1 200 1e-6 2 ${NODES1}                     # una riga per rank
    check small8 out/small8.pgm 1 200 1e-6 8 ${NODES1}                 # una riga per rank
    for p in 2 3 4 16; do check small images/small/noisy.pgm 1 200 1e-6 "$p" ${NODES1}; done   # 17 righe: strisce irregolari
    for p in 3 16; do check small-fisso images/small/noisy.pgm 1 200 0 "$p" ${NODES1}; done
    for p in 2 4 8 16; do check medium images/medium/noisy.pgm 1 200 1e-6 "$p" ${NODES1}; done
    check medium-l02 images/medium/noisy.pgm 0.2 200 1e-6 16 ${NODES1} ;;
nodi)
    echo "--- nodi usati da 17 rank:"
    $LAUNCH 17 ${NODES2} hostname | sort | uniq -c
    check small images/small/noisy.pgm 1 200 1e-6 17 ${NODES2}         # una riga per rank, due nodi
    check medium images/medium/noisy.pgm 1 200 1e-6 32 ${NODES2}
    check medium-fisso images/medium/noisy.pgm 1 50 0 32 ${NODES2}
    echo "--- atteso un errore: 18 rank per 17 righe"
    $LAUNCH 18 ${NODES2} ./denoise_mpi images/small/noisy.pgm out/err.pgm 1 200 1e-6 2>&1 | grep -m1 Require ;;
*)
    echo "Uso: bash test_mpi.sh uno | nodo | nodi" >&2; exit 1 ;;
esac
