# Local / cluster configuration

`cluster.example.env` records the non-secret WILSON connection values used by
this project:

```text
fbellina2@wilson.mib.infn.it
```

A remote working path is deliberately not hard-coded because it should be taken
from the exercise instructions or confirmed in the laboratory.

If a future helper script needs machine-local values, copy the example file:

```bash
cp config/cluster.example.env config/cluster.env
```

`config/cluster.env` is ignored by Git. Never store passwords, private keys,
GitHub tokens, or other credentials in either file.
