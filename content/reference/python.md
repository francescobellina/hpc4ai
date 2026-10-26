# Riferimento Python

Python è disponibile sul client e su WILSON, ma in ambienti diversi: controlla
dove gira il comando e quale ambiente è attivo.

```bash
python        # client locale; esci con exit() o Ctrl+D
```

Gli appunti del corso riportano un virtual environment preinstallato su WILSON.
Verifica percorso e disponibilità nell'ambiente effettivo prima di attivarlo:

```bash
source /srv/software2/venv/python39/bin/activate
python        # ora punta al venv
ipython       # shell interattiva
```

Il percorso `/srv/software2/venv/python39/bin/activate` compare negli appunti, ma
non è una configurazione WILSON verificata in questo repository.

## JupyterHub

<https://wilson.mib.infn.it/jupyter>

- l'indirizzo e l'accessibilità dipendono dalle istruzioni aggiornate del corso;
- login con le credenziali WILSON;
- kernel Python e Julia; utile anche per copiare e spostare file.

Il kernel gira su WILSON: chiudere la scheda del browser non sposta l'esecuzione
sul client.
