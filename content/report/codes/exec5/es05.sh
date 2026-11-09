#!/usr/bin/env bash
# Esercitazione 5 (benchmarking e scaling, HPL e HPCG) su WILSON.
#
#   bash es05.sh setup     # ricognizione, copia dei file del corso, baseline
#   bash es05.sh collect   # raccoglie input, output e sacct di tutti i run
#
# Va eseguito sul login node. Lavora in ~/es05/: una cartella per configurazione
# (input + script batch + output), come chiede la consegna. Ogni comando viene
# scritto con il suo output in ~/es05/logs/<sottocomando>_<data>.txt, il file da
# scaricare.
set -uo pipefail

REF=${REF:-/srv/data/wilson/project/hpc4ai/exercises/benchmark}
ES=${ES:-$HOME/es05}
SACCT_FMT=JobID,JobName%24,Partition,NodeList%24,NNodes,NTasks,AllocCPUS,ReqMem,Timelimit,Elapsed,State,ExitCode

section() { printf '\n========== %s ==========\n' "$*"; }
# cmd stampa il comando dopo un prompt reale (utente, macchina, cartella) e lo esegue.
prompt() { printf '[%s@%s %s]$ ' "${USER:-$(id -un)}" "$(hostname -s)" "${PWD##*/}"; }
cmd() { printf '%s%s\n' "$(prompt)" "$*"; "$@" 2>&1; }
is_text() {
    if command -v file >/dev/null; then
        file -b --mime-type "$1" | grep -q '^text/'
    else
        case $1 in *.dat|*.sh|*.txt|*README*) true ;; *) false ;; esac
    fi
}

# submit <cartella>: invia lo script batch della cartella e ne salva il job ID.
submit() {
    local dir=$1 script id
    script=$(cd "$dir" && ls ./*.sh 2>/dev/null | head -1)
    [ -n "$script" ] || { echo "Nessuno script batch in $dir"; return 1; }
    if [ -f "$dir/.jobid" ]; then
        echo "$dir: già inviato (job $(cat "$dir/.jobid")), non lo reinvio"
        return 0
    fi
    cd "$dir" || return 1
    printf '%s%s\n' "$(prompt)" "sbatch --parsable $script"
    id=$(sbatch --parsable "$script") && echo "${id%%;*}" > .jobid && echo "job ${id%%;*}"
    cd - >/dev/null || return 1
}

do_setup() {
    section "0. Login node"
    cmd date
    cmd hostname
    echo "MODULEPATH=${MODULEPATH:-}"

    section "1. File di riferimento del corso"
    cmd ls -l "$REF"
    cmd sha256sum "$REF"/*
    local f
    for f in "$REF"/*; do
        [ -f "$f" ] && is_text "$f" && cmd cat "$f"
    done

    section "2. Partizioni e nodi"
    cmd sinfo -p wilson,wilson2,lab4 -o "%P %a %l %D %c %m %f %N"
    cmd sinfo -N -p lab4 -o "%N %P %c %m %f %T"

    section "3. Moduli"
    if type module >/dev/null 2>&1; then
        cmd module spider HPL
        cmd module spider HPCG
    else
        echo "(module non inizializzato in questa shell)"
    fi

    section "4. Cartelle di lavoro in $ES"
    mkdir -p "$ES"/{reference,hpl,hpcg,nodeinfo,logs}
    cp -n "$REF"/* "$ES/reference/" 2>/dev/null
    mkdir -p "$ES/hpl/00_baseline" "$ES/hpcg/00_baseline"
    cp -n "$REF"/HPL.dat "$REF"/HPL*.sh "$ES/hpl/00_baseline/"
    cp -n "$REF"/hpcg.dat "$REF"/HPCG*.sh "$ES/hpcg/00_baseline/"
    cmd ls -l "$ES/reference" "$ES/hpl/00_baseline" "$ES/hpcg/00_baseline"

    section "5. CPU dei due tipi di nodo (job brevi, raccolti da collect)"
    local p
    for p in wilson wilson2; do
        if ls "$ES"/nodeinfo/lscpu_"$p".*.out >/dev/null 2>&1; then
            echo "lscpu su $p già raccolto"
            continue
        fi
        cd "$ES/nodeinfo" || return 1
        printf '%s%s\n' "$(prompt)" "sbatch -p $p -N 1 -n 1 --mem=1G -t 00:02:00 -o lscpu_$p.%j.out --wrap 'hostname; lscpu'"
        sbatch -p "$p" -N 1 -n 1 --mem=1G -t 00:02:00 -o "lscpu_$p.%j.out" --wrap 'hostname; lscpu' 2>&1
        cd - >/dev/null || return 1
    done

    section "6. Baseline con i file del corso non modificati"
    submit "$ES/hpl/00_baseline"
    submit "$ES/hpcg/00_baseline"
    cmd squeue -u "${USER:-$(id -un)}"
}

do_collect() {
    section "0. Stato dei job"
    cmd date
    cmd squeue -u "${USER:-$(id -un)}"

    section "1. CPU dei nodi"
    local f dir id
    for f in "$ES"/nodeinfo/*.out; do
        [ -f "$f" ] && cmd cat "$f"
    done

    for dir in "$ES"/hpl/*/ "$ES"/hpcg/*/; do
        [ -f "$dir/.jobid" ] || continue
        id=$(cat "$dir/.jobid")
        section "${dir#"$ES"/} (job $id)"
        cd "$dir" || continue
        cmd ls -l
        for f in *.dat *.sh; do
            [ -f "$f" ] && cmd cat "$f"
        done
        cmd sacct -j "$id" --format="$SACCT_FMT"
        for f in *.out HPCG-Benchmark*.txt; do
            [ -f "$f" ] && cmd cat "$f"
        done
        for f in *.out; do
            [ -f "$f" ] || continue
            cmd grep -E "WR[0-9A-Z]+ |PASSED|FAILED" "$f"
        done
        for f in HPCG-Benchmark*.txt; do
            [ -f "$f" ] && cmd grep "Final Summary" "$f"
        done
        cd - >/dev/null || return 1
    done
}

case "${1:-}" in
    setup|collect) ;;
    *) echo "Uso: bash es05.sh setup | collect" >&2; exit 1 ;;
esac
command -v sbatch >/dev/null || { echo "Errore: sbatch non trovato, non sei su WILSON?" >&2; exit 1; }
mkdir -p "$ES/logs"
LOG="$ES/logs/$1_$(date +%Y%m%d_%H%M%S).txt"
cd "$HOME" || exit 1
"do_$1" 2>&1 | tee "$LOG"
echo
echo "Log da scaricare: $LOG"
