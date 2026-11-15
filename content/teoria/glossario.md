# Glossario e domande di controllo

Vocabolario comune a tutti i capitoli di teoria e agli esercizi, in linguaggio semplice, con domande di autoverifica. I concetti sono spiegati per esteso nei capitoli 1–6.

## Glossario rapido

| Termine | Significato |
|---|---|
| Core | Unità di esecuzione indipendente dentro la CPU |
| Thread hardware (SMT) | CPU logica offerta da un core, che condivide le unità di calcolo |
| Processo | Programma in esecuzione, con il proprio spazio di indirizzi |
| Thread | Flusso di esecuzione dentro un processo, con memoria condivisa |
| Cache | Copia piccola e veloce dei dati tenuta vicino al core |
| Cache line | Blocco di memoria trasferito tutto insieme, di solito 64 byte |
| Hit / miss | Accesso servito dalla cache / accesso che deve scendere di livello |
| Associatività | Numero di posti che un blocco può occupare nel suo set |
| Tag, index, offset | Campi in cui l'indirizzo viene spezzato per cercare in cache |
| Località | Tendenza a riusare dati recenti e dati vicini |
| Prefetching | Caricamento anticipato quando il pattern di accesso è prevedibile |
| False sharing | Variabili indipendenti nella stessa cache line, contese dai core |
| TLB | Cache delle traduzioni da indirizzo virtuale a fisico |
| NUMA | Memoria la cui latenza dipende dal socket a cui è collegata |
| Latenza | Tempo per ottenere un singolo dato |
| Banda | Byte trasferiti al secondo |
| Complessità O(f) | Come cresce il costo quando cresce la dimensione dell'input |
| Speedup, efficienza | `T1/Tp`; speedup diviso per il numero di processori |
| Legge di Amdahl | Limite allo speedup imposto dalla parte seriale del codice |
| Strong / weak scaling | Stesso problema con più processori / problema che cresce con loro |
| Squilibrio del carico | Distribuzione diseguale del lavoro fra thread o processi |
| Concorrenza / parallelismo | Attività che avanzano insieme / attività che girano nello stesso istante |
| SIMD | Una istruzione applicata a più dati in un colpo solo |
| GIL | Lock di CPython che serializza il bytecode Python fra thread |
| Race condition | Accesso concorrente non sincronizzato, risultato non deterministico |
| Reduction | Combinazione sicura di valori parziali (somma, massimo) a fine regione |
| Fork-join | Modello in cui un master crea un team di thread e poi si ricongiunge |
| Barrier | Punto in cui tutti i thread o i processi attendono gli altri |
| Rank | Identificativo di un processo MPI |
| Communicator | Gruppo di processi MPI che possono comunicare |
| Collective | Operazione MPI che coinvolge tutti i processi del communicator |
| SPMD | Modello in cui tutti i processi eseguono lo stesso programma su dati diversi |
| Deadlock | Stallo in cui processi o thread si aspettano a vicenda per sempre |
| Halo / celle fantasma | Copie dei bordi ricevute dai vicini |

## Domande di controllo

::::{dropdown} 1. Perché la cache trasferisce linee da 64 byte e non byte singoli?

Il costo di una richiesta alla RAM è dominato dalla latenza, non dal payload:
portare 64 byte costa quasi quanto portarne 8. Inoltre i byte vicini a quello
richiesto serviranno quasi subito (località spaziale), quindi non sono
sprecati.

:::

::::{dropdown} 2. Una cache L1 da 32 KB ha linee da 64 byte e associatività 8. Quanti set, e quanti bit di index?

32768 / (64 x 8) = 64 set, quindi 6 bit di index (2^6 = 64) e 6 bit di offset;
i bit restanti dell'indirizzo sono il tag.

:::

::::{dropdown} 3. Un hit dura 1 ns, il miss rate è 3%, la penalità di miss è 100 ns. Qual è il tempo medio di accesso?

AMAT = 1 + 0,03 x 100 = 4 ns.

:::

::::{dropdown} 4. Che differenza c'è tra latenza e banda? Quanti byte devono essere in volo con 100 ns di latenza e 50 GB/s di banda?

La latenza è il tempo per ottenere un dato; la banda è quanti byte al secondo
passano una volta partito il flusso. Byte in volo = latenza x banda =
100e-9 x 50e9 = 5000 byte, cioè circa 80 cache line.

:::

::::{dropdown} 5. Perché sommare una matrice per colonne può essere molto più lento che per righe?

Gli elementi di una matrice sono memorizzati per righe, quindi sommare per
righe usa tutta la linea da 64 byte caricata. Sommare per colonne salta di
`n x 8` byte a ogni passo, e ogni elemento richiede una linea diversa. Se
`n x 8` è una potenza di 2 (per esempio n = 512), tutti gli elementi di una
colonna finiscono nello stesso set e si accumulano i conflict miss.

:::

::::{dropdown} 6. Se il 10% di un programma è seriale, qual è lo speedup massimo?

Legge di Amdahl: S(infinito) = 1 / 0,1 = 10. Nessun numero di processori può
fare meglio.

:::

::::{dropdown} 7. Perché i thread Python non accelerano il calcolo Python puro, mentre NumPy sì?

Il GIL permette a un solo thread alla volta di eseguire bytecode Python, quindi
i thread si alternano invece di lavorare insieme. NumPy esegue il ciclo in C e
rilascia il GIL durante il calcolo, così più thread lavorano davvero in
parallelo.

:::

::::{dropdown} 8. Cosa succede se più thread OpenMP incrementano la stessa variabile senza `reduction`?

Si verifica una race condition: alcuni incrementi si perdono, e il risultato
è sbagliato e diverso da un'esecuzione all'altra. Con `reduction` ogni thread
accumula in una copia privata e le copie vengono sommate alla fine.

:::

::::{dropdown} 9. Perché due processi MPI che fanno entrambi `Send` prima di entrambi `Recv` possono bloccarsi?

Con messaggi grandi il protocollo rendezvous attende che il ricevente sia
pronto, ma entrambi i processi sono bloccati in `Send`, quindi nessuno riceve
mai. Si risolve con `Sendrecv`, oppure rendendo asimmetrico l'ordine fra rank
pari e dispari.

:::

::::{dropdown} 10. Un algoritmo O(n^2): quanto più lento quando n raddoppia?

Quattro volte più lento, perché (2n)^2 = 4n^2.

:::
