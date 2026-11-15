# HPC launch scripts

[Repository index](../AGENTS-docs.md) · [Other utilities](../utils/AGENTS-docs.md)

| File | Responsibility and dependencies |
| --- | --- |
| `snellius_env.sh` | Must be sourced; explicitly rejects execution as a subshell. Loads SURF's 2021 module collection, CMake, GCC, parallel HDF5, and OpenMPI. Requires the cluster's `module` environment and named module versions. |
| `cartesius_job.sh` | Single-case Slurm template: short partition, 384 tasks, runs `mpirun -n 384 ./hemoFlow setup.xml` from the submission working directory. Not the recursive batch runner in `utils/`. |
| `AGENTS-docs.md` | This script index. |

The job template assumes the binary and XML are in the working directory, not CMake's `build/` location. Replace the legacy XML and adjust paths, task counts in both Slurm/MPI settings, and partition before submission. These scripts do not build the solver or preprocess geometry.
