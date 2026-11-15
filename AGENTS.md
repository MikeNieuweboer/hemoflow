# HemoFlow working notes

## Exploration
- Each folder contains and AGENTS-docs.md file with summaries of the functionality of each file and subfolder, along with their dependencies between eachother. These are created as an indexing tool for agents, but are also human readable.
- These files have been constructed before, but are to be updated whenever any important architectural changes are made, including, new files, changes in dependencies or changes in the overal function of a file.
- The Palabos and external libraries are excluded from this procedure, while they can still be referenced as dependency.

## Build and verification
- Configure from the repository root: `cmake -S . -B build`; build the solver with `cmake --build build --target hemoFlow -j 2`. Release is the default; use `-DCMAKE_BUILD_TYPE=Debug` to enable `PLB_DEBUG`.
- MPI and parallel HDF5 are required by the application code, despite the `ENABLE_MPI`/`BUILD_HDF5` switches and CMake's serial-HDF5 fallback message. MPI shared-memory windows and HighFive MPI-IO calls are unconditional.
- The root CMake file does not add `external/HighFive/include/highfive` for the `<H5*.hpp>` headers in `globals.h`, nor explicitly link zlib used by cnpy. Investigate these omissions if compilation/linking fails; do not assume a clean build is already supported.
- `palabos/` is checked in and compiled directly by the root CMake file, not via its own CMake project. Do not run `setup.sh` to provision it: that script only tries to clone into the existing directory. `external/` contains bundled HighFive and cnpy.
- On the SURF module environment, use `source scripts/snellius_env.sh`, not `bash scripts/snellius_env.sh`.
- There is no application test/lint/typecheck target or root CI workflow. Tests under bundled dependencies are not solver tests; `preprocessorlbm_versatile/test.py` is a manual inspection script with absolute external-data paths, not a test suite.

## Execution and data contract
- Run `mpirun -n <ranks> ./build/hemoFlow /path/to/config.xml`; append `-r` to resume checkpoints in the configured output directory. Optional `<simulation><checkpointFrequency>` enables checkpoint writing.
- Use `ExampleXML.xml` as the configuration starting point, replacing its machine-specific paths. Root `setup.xml` is an older incompatible schema. Confirm required tags against XML reads in `hemoFlow.cpp`; flowrate files contain flowrates, not velocities.
- The current solver consumes two geometry files: `<geometry><file>` points to `*ops.npz` (opening metadata plus `Nx`, `Ny`, `Nz`), and `<geometry><GeometryFlag>` points to `*gf.h5` (flattened int8 dataset `geometryFlag`).
- `hemoFlow.cpp` wires XML/data loading, MPI shared geometry, boundary setup, time stepping, and output. `opening.cpp` handles opening boundary profiles; `globals.h` selects lattice dynamics and defines geometry labels; `porous.h` implements flow-diverter behavior.

## Preprocessing and geometry changes
- Use `python preprocessorlbm_versatile/main.py /path/to/input.config` for the current split NPZ/HDF5 format. `preprocessor/main.py` instead writes the legacy combined `*c.npz`; the directories are not interchangeable. Both `run.sh` examples use obsolete positional arguments.
- The versatile JSON config requires `geometry_dir`, `geometry_original_stl`, `centerline_vtp`, `stent_mesh_base` (empty when unused), `output_base_name`, and `target_elements`. Input geometry paths are relative to `geometry_dir`; outputs go beside the config. Supply a config path with a directory component: the script concatenates `dirname(config) + "/"` for outputs.
- Python imports require NumPy, VTK, numpy-stl, and h5py; pynrrd is additionally needed for debug NRRD output. No dependency lockfile is provided. `SI_FACTOR = 0.001` in `main.py` assumes STL units are millimeters; centerline VTP must contain `MaximumInscribedSphereRadius`.
- Geometry support is hardcoded for this multi-inlet case. Changes must reconcile `preprocessorlbm_versatile/readCL.py` (`inlet_line_ids`/tangent direction), `detectOpenings.py` (`paint_dic`), Python `constants.py`, C++ `globals.h`, flowrate indexing/boundaries in `hemoFlow.cpp`, and pressure-outlet logic in `opening.cpp`.
- Labels 10–14 are five distinct inlets and 15–18 are outlets. Although `globals.h` calls 18 the pressure outlet, active `opening.cpp::setBC` applies virtual-outlet boundaries to all labels >= 15; time-dependent outlet density updates are disabled. The preprocessor README's older single-inlet flag table does not describe the current solver. The solver reads ten fixed flowrate-function entries regardless of the configured count; changing only XML does not generalize the geometry.
