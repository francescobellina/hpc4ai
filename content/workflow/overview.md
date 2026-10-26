# Ambiente di lavoro e sincronizzazione

Il repository distingue tre ambienti: sviluppo locale, sincronizzazione Git e calcolo remoto. Mac e PC di laboratorio ospitano copie locali del repository; GitHub è il punto di sincronizzazione; WILSON è un ambiente separato, raggiunto quando l'esercizio richiede risorse HPC.

## Sviluppo locale

Sul Mac, il percorso usato da questo progetto è `/Users/francesco/dev/hpc4ai`. Sul PC di laboratorio, lavora nella cartella del clone. Apri la directory del progetto in VS Code e controlla sempre la directory corrente prima di eseguire un comando.

Per preparare l'ambiente del libro e avviare l'anteprima, il repository fornisce questi script:

```bash
./scripts/setup-env.sh
./scripts/preview.sh
```

Per i controlli di qualità e la build:

```bash
./scripts/check.sh
./scripts/build.sh
```

Usa `./scripts/clean.sh` solo quando vuoi rimuovere l'output generato `_build/`. Gli script e le attività VS Code sono definiti nel repository; l'ambiente Python è locale e non è l'ambiente di WILSON.

In VS Code, **Terminal -> Run Task** espone attività per setup e anteprima del libro, build e check, pulizia dell'output, stato Git, pull `--ff-only`, push e SSH WILSON. Usa l'attività SSH solo da una rete che può raggiungere il cluster.

## Git tra le due postazioni

Al primo utilizzo, clona il repository del corso sul PC di laboratorio:

```bash
git clone https://github.com/francescobellina/hpc4ai.git
cd hpc4ai
```

Clonalo una sola volta. All'inizio di una sessione controlla le modifiche e aggiorna solo se Git può avanzare senza creare un merge automatico:

```bash
git status
git pull --ff-only
```

Dopo un'unità di lavoro coerente:

```bash
git add -A
git status
git commit -m "Descrivi la modifica"
git push
```

Al ritorno sull'altra postazione, esegui `git status` e `git pull --ff-only` prima di modificare gli stessi file. Se il pull rifiuta, ispeziona lo stato e la cronologia con `git log --oneline --decorate --graph -10`; non forzare l'aggiornamento.

## Organizzazione del progetto

Le lezioni sono sotto `content/lectures/`, gli strumenti generali sotto `content/reference/` e la relazione di laboratorio sotto `content/report/`. Codice completo, notebook, figure e risultati restano vicini al materiale che li usa. Il TOC del libro è `toc.yml`; la configurazione MyST è `myst.yml`.

Per l'accesso, i trasferimenti e l'esecuzione su WILSON, consulta la [guida pratica al cluster](lab-client-wilson.md). Non confondere il clone locale con la directory remota e non salvare credenziali nel repository.
