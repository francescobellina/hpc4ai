/* Stampa la configurazione di un modello llama2.c (le 7 int dell'intestazione) e la
   dimensione del file, per stimare i byte letti per token.
   vocab_size negativo significa classificatore con pesi propri (non condivisi). */
#include <stdio.h>

int main(int argc, char **argv)
{
    for (int a = 1; a < argc; ++a) {
        FILE *f = fopen(argv[a], "rb");
        if (!f) { perror(argv[a]); return 1; }
        int c[7];
        if (fread(c, sizeof(int), 7, f) != 7) { fprintf(stderr, "%s: intestazione corta\n", argv[a]); return 1; }
        fseek(f, 0, SEEK_END);
        long bytes = ftell(f);
        fclose(f);
        printf("%s: dim=%d hidden_dim=%d n_layers=%d n_heads=%d n_kv_heads=%d vocab_size=%d seq_len=%d bytes=%ld\n",
               argv[a], c[0], c[1], c[2], c[3], c[4], c[5], c[6], bytes);
    }
    return 0;
}
