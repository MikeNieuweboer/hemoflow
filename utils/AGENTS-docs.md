# Operational utilities

[Repository index](../AGENTS-docs.md) · [Environment/single-case scripts](../scripts/AGENTS-docs.md)

| File | Responsibility and dependencies |
| --- | --- |
| `cartesius_job.sh` | Slurm batch template for multiple cases. Captures the launch directory, finds XML files under its `data/`, changes into each case directory, and sequentially runs the launch-directory `hemoFlow` with 384 MPI ranks. Unlike `scripts/cartesius_job.sh`, uses normal partition and Haswell constraint. Requires Slurm/MPI and externally supplied cases. |
| `compress_output.py` | Uses Python VTK to recursively read `.vti` and rewrite to sibling `*_c.vti` files, skipping existing compressed outputs. Retains originals; does not handle `.h5`/`.xmf`. Same active behavior as root `compress_output.py`. |
| `update_times.sh` | Recursively runs `touch` on every file below each argument, intended for scratch-storage retention. Mutates timestamps rather than content; contains a stray line of DEL control characters before the loop. |
| `AGENTS-docs.md` | This utility index. |

- VTI command from root: `python utils/compress_output.py /path/to/output/`. Keep the trailing slash: the implementation concatenates the directory directly with `**/*.vti`.
- Batch runner paths are based on its launch directory, not the script location. Its shell loop splits `find` output on whitespace; do not assume case paths containing spaces work. Align Slurm/MPI rank counts and point the executable to the actual CMake build before using it.
