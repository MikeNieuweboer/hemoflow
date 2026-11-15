# Repository index

Working instructions and commands: [AGENTS.md](AGENTS.md). This index describes wiring and ownership; update the affected directory indexes when files, dependencies, or responsibilities change. Git internals and bundled `palabos/` and `external/` trees are excluded from indexing.

## Execution map

`STL + centerline VTP + JSON config` → [current preprocessor](preprocessorlbm_versatile/AGENTS-docs.md) → `*ops.npz + *gf.h5` → `hemoFlow.cpp` with XML configuration → HDF5/XMF output and optional checkpoints.

The [legacy preprocessor](preprocessor/AGENTS-docs.md) writes a different, combined NPZ format. Neither preprocessor is run by CMake.

## Files

| File | Responsibility and dependencies |
| --- | --- |
| `hemoFlow.cpp` | Solver entrypoint. `calcSimulationParameters` converts physical/lattice units; `processOpenings` assigns profiles and flowrate functions; `writeHDF5` writes parallel HDF5 and XMF; `main` loads XML/NPZ/HDF5, shares geometry through MPI windows, builds the lattice, advances time, and handles checkpoints. Includes all four local headers below, cnpy, and Palabos XDMF support. |
| `globals.h` | Shared numeric type, lattice descriptor/background dynamics, geometry labels, and external `Nx/Ny/Nz` definitions (storage in `hemoFlow.cpp`). Pulls in Palabos and HighFive headers. Python labels must agree with these constants. |
| `helper.h` | Flat-array indexing, interpolation, vectors/tensors, and Palabos flag-mask domain functors. Depends on `globals.h`; consumed by opening and porous code. `gT(x,y,z)` is `x*Ny*Nz + y*Nz + z`, matching NumPy's default flattening for `(Nx,Ny,Nz)`, despite its misleading Fortran-order comment. |
| `opening.h` | Declares `OpeningHandler` and velocity/pressure profile functors; depends on `globals.h` and `helper.h`. |
| `opening.cpp` | Implements node collection by label, opening geometry, blunt/Poiseuille profiles, signal loading/interpolation, and boundary setup. Flowrate text starts with a sample count followed by time/Q pairs; Q is divided by circular area. Currently labels below `OUTLET_RPA` get velocity boundaries; all outlets get `VirtualOutlet`, and their time-dependent density update is disabled. |
| `porous.h` | Palabos processors to initialize porosity and apply linear/quadratic velocity-dependent drag; depends on `globals.h`/`helper.h`. The hookup in `hemoFlow.cpp` is commented out, so these definitions do not imply active porous forcing. |
| `CMakeLists.txt` | Builds static Palabos from `palabos/src/*.cpp` plus TinyXML, then links `hemoFlow.cpp`, `opening.cpp`, and cnpy into `hemoFlow`. Finds MPI/HDF5; see `AGENTS.md` for dependency/configuration omissions. |
| `ExampleXML.xml` | Current configuration example, including separate fluid, geometry, simulation, and flow-diverter sections; references external absolute paths. |
| `setup.xml` | Legacy configuration; lacks the sections/fields required by the current solver. |
| `README.md` | Feature history, limitations, and TODOs. Line references and descriptions can lag active source. |
| `setup.sh` | One-line clone of upstream Palabos; not an installer for this already-vendored tree. |
| `compress_output.py` | VTK-based recursive VTI rewrite to sibling `*_c.vti` files; same active behavior as the utility copy. Pass a directory with a trailing `/` because it concatenates the glob directly. Does not process HDF5 output. |
| `.gitignore` | Excludes build, output, compiled artifacts, and Python caches; Palabos is deliberately not ignored. |
| `AGENTS.md` | Repository-wide working instructions, prerequisites, commands, and cross-language constraints. |
| `AGENTS-docs.md` | This navigation and dependency map. |

## Directories

| Directory | Responsibility |
| --- | --- |
| [preprocessorlbm_versatile/](preprocessorlbm_versatile/AGENTS-docs.md) | Current multi-inlet geometry pipeline and split solver input writer. |
| [preprocessor/](preprocessor/AGENTS-docs.md) | Legacy single-inlet pipeline and combined NPZ writer. Modules are separate copies, not a shared package. |
| [scripts/](scripts/AGENTS-docs.md) | SURF environment setup and single-case Slurm template. |
| [utils/](utils/AGENTS-docs.md) | Batch-case Slurm template, VTI processing, and timestamp utility. |
| [doc/](doc/AGENTS-docs.md) | Manual ParaView postprocessing recipe. |
| `palabos/` | Bundled LBM implementation, MPI support, I/O, and examples. Root CMake consumes source directly; excluded from indexing. |
| `external/` | Bundled cnpy (NPZ reader; zlib) and HighFive (C++ HDF5 wrappers). HighFive headers live under `external/HighFive/include/highfive/`; excluded from indexing. |
