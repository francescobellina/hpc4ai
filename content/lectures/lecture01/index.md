# Lecture 1 — From the client to WILSON

This lecture establishes the operational workflow used throughout the course.
The emphasis is on knowing **where** code is edited, synchronized, transferred,
and executed.

It follows the structure of the course warm-up exercise *From the client to
WILSON*, while integrating the personal GitHub/VS Code workflow used by this
repository.

## Confirmed environments

| Environment | Role |
|---|---|
| Mac / VS Code | Main development environment at `/Users/francesco/Desktop/hpc4ai` |
| GitHub | Canonical repository: `francescobellina/hpc4ai` |
| Lab PC / client | Local laboratory clone and client for cluster exercises |
| WILSON | Remote HPC environment reached as `fbellina2@wilson.mib.infn.it` |

## Learning objectives

By the end of the lecture, you should be able to:

- distinguish the Mac, lab client, GitHub, and WILSON environments;
- create the course local workspace using the WILSON username `fbellina2`;
- synchronize the repository between the Mac and the lab PC;
- transfer exercise files between the lab client and WILSON when required;
- recognize whether a command belongs on the local client or on WILSON;
- inspect the Lmod environment without inventing module names;
- preserve source code and useful results in a reproducible way.

## Course exercise sequence

1. Create a local workspace.
2. Write and compile the program.
3. Configure and run it locally.
4. Transfer the source and connect to WILSON.
5. Prepare the software environment on WILSON with Lmod.
6. Run remotely and save the result.
7. Copy the result back and preserve the local work.

## Structure

1. [Theory and workflow concepts](theory.md)
2. [Worked examples](examples.md)
3. [Exercises](exercises/index.md)

The WILSON username and hostname are confirmed in this project. Remote working
paths, exact module names, compiler versions, and scheduler commands remain
exercise-specific and must not be guessed.
