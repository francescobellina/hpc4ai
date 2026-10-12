# Riferimento Python

Python è disponibile sul client e su WILSON, ma in ambienti diversi: controlla
dove gira il comando e quale ambiente è attivo.

```bash
python        # client locale; esci con exit() o Ctrl+D
```

Su WILSON le librerie per HPC e machine learning sono in un virtual environment
preinstallato: attivalo prima di usare Python.

```bash
source /srv/software2/venv/python39/bin/activate
python        # ora punta al venv
ipython       # shell interattiva
```

Il path del venv è quello del corso: confermalo su WILSON prima di usarlo.

## JupyterHub

<https://wilson.mib.infn.it/jupyter>

- accessibile solo dalla rete del laboratorio;
- login con le credenziali WILSON;
- kernel Python e Julia; utile anche per copiare e spostare file.

Il kernel gira su WILSON: chiudere la scheda del browser non sposta l'esecuzione
sul client.
