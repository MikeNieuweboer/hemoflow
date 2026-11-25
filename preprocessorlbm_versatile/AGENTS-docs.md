# Current geometry preprocessor

[Repository index](../AGENTS-docs.md) · [Legacy pipeline](../preprocessor/AGENTS-docs.md)

Run from the repository root: `python preprocessorlbm_versatile/main.py /path/to/input.config`. This directory uses bare sibling imports, not a Python package shared with `preprocessor/`.

## Flow and dependencies

1. `main.py` reads JSON; `geometry_dir` locates STL/VTP inputs and resolves the output prefix. Required keys and units are documented in [AGENTS.md](../AGENTS.md).
   The CLI accepts the config path, `--debug`, and `--log-to-file`. The latter appends `<output_base_name>preprocessing.log` in `work_dir` (the geometry directory) as well as logging to stderr. `--debug` enables DEBUG in both destinations and NRRD output. Module loggers propagate to entrypoint-owned handlers in `logging_setup.py`; workers do not log. In current `main.py`, `si_factor` and `cut_width` are required and `distance` is not read.
2. `voxelizeStl.py` uses numpy-stl → `slice.py` triangle intersections → `perimeter.py` rasterization; `util.py` pads the result. Internal slice order is rearranged to `(x,y,z)` before return.
3. `readCL.py` uses VTK to extract endpoint radii, centers, and tangents, then converts positions to voxel space. `main.py::generate_cut_list` selects bounding-box faces whose Manhattan distance from any endpoint is at most that endpoint's radius, using the original geometry coordinates rather than a fixed voxel distance. Face indices are x-min, x-max, y-min, y-max, z-min, z-max. `main.py` then calls `createFluidSolid.py` to paint walls/fluid.
4. `detectOpenings.py` groups and paints openings using `constants.py`; `main.py` matches centers to centerline endpoints, then saves metadata and geometry separately.
5. The root solver reads `*ops.npz` and `*gf.h5`. Label changes also affect root `globals.h`, `hemoFlow.cpp`, and `opening.cpp`.

Dependencies: NumPy, numpy-stl, VTK, h5py; pynrrd for debug output. The commented connected-component alternative would additionally use SciPy, but is not active.

Function signatures use concrete lists/tuples for geometry and opening data, explicit `Generator` return types for functions using `yield`, and plain `np.ndarray` for NumPy arrays (no shape or dtype constraints).

## Files

| File | Responsibility |
| --- | --- |
| `config.template.json` | Copyable JSON configuration template containing required input/output fields and optional preprocessing settings with their defaults. |
| `main.py` | Pipeline/JSON entrypoint. `main()` configures console logging and catches unexpected exceptions; `run_preprocessing()` resolves inputs and optional file logging, then runs the pipeline. Writes `output_base_name + "openings.npz"` with opening arrays, `dx`, and dimensions; writes `output_base_name + "geometry.h5"` with gzip-compressed flattened int8 `geometryFlag`. No stent voxelization runs here. |
| `logging_setup.py` | Standard-library logging configuration shared by entrypoints: timestamp/level/module formatting, console output and optional UTF-8 append-only file output, replacing only its own handlers on repeated setup. Imported processing modules never configure handlers. |
| `test_logging.py` | Unittest checks for console/file verbosity, append behavior, duplicate prevention, caller-handler preservation, file/config failures, CLI flags, module diagnostics, and unchanged wall-array expectations. Run `python -m unittest test_logging`. |
| `voxelizeStl.py` | STL loading, scale/shift, slice rendering, padding, and axis swaps. Uses 16 workers with a local `fork` context and an initializer that stores inherited geometry per worker; tasks send only slice heights, avoiding repeated mesh serialization and allowing repeated calls without resetting the global start method. |
| `slice.py` | Triangle/plane intersections, interpolation, bounding-box-based target resolution, transforms, and axis swaps. Imports `perimeter.py` and distance/deduplication helpers from `util.py`. |
| `perimeter.py` | Converts slice line segments to filled or shell voxel planes; line selection/intersection helpers. NumPy-based, called by the voxelizer. |
| `util.py` | Array padding, point deduplication, Manhattan distance, and array/pixel inspection helpers used by voxelization/slicing. |
| `readCL.py` | VTP reader requiring `MaximumInscribedSphereRadius`. `inlet_line_ids = [4,5,6,7]` and first-line inlet handling control tangent signs for this specific centerline. |
| `createFluidSolid.py` | Zero-padded neighbor shifts expand the fluid mask into wall cells, trim empty bounds, and cut chosen domain faces. Returns int8 geometry plus crop bounds; imports multiprocessing but the wall calculation is serial. |
| `detectOpenings.py` | Active method scans surface voxels and recursively groups plane-aligned openings; connected-component code is commented out. `paint_dic` maps discovery order to named inlet/outlet labels. `detectOpenings()` currently discards its padded copy and slices one layer off the final result; check dimensions/centers when changing padding. |
| `constants.py` | Unused/wall/fluid labels 0/1/2, inlets 10–14, outlets 15–18. Must match root `globals.h`; old README flag tables do not apply. |
| `view_nrrd.py` | Standalone debug NRRD viewer using NumPy, pynrrd, PyVista (VTK), `constants.VoxelType`, and `voxel_surface.py`. Renders exact label boundaries in voxel coordinates with stable colors, visibility checkboxes, opacity sliders, and optional screenshots/off-screen rendering; no intermediate unstructured volume. |
| `voxel_surface.py` | NumPy-only boundary mesher. Scans neighboring planes and merges equal-label exposed face runs into coplanar rectangles with outward winding. Returns compact point/connectivity buffers per label, retaining both sides of label interfaces for independent visibility. Temporary masks are plane-sized; final memory depends on boundary complexity. |
| `test_voxel_surface.py` | NumPy-only unittest checks comparing merged geometry against reference unit faces, including winding, interfaces, holes, thin dimensions, unknown labels, and array layouts. Run from this directory with `python -m unittest test_voxel_surface`. |
| `README.md` | Inherited usage/geometry notes; single-inlet assumptions and flag table are stale for this variant. |
| `run.sh` | Obsolete multi-positional-argument example; does not match `main.py`'s single JSON-config argument. |
| `test.py` | Manual comparison of opening tangents from absolute-path external NPZ files, with commented mutation examples; no assertions or portable test fixture. |
| `check.ipynb` | Ad hoc NumPy inspection of local `voxels.npy`, including a NaN check; no pipeline integration. |
| `AGENTS-docs.md` | This pipeline/file index. |

## Cross-file constraints

- NPZ opening arrays must stay in the same matched order; radii and `dx` are converted to meters using `SI_FACTOR = 0.001`, but centers remain voxel coordinates.
- Geometry is flattened with NumPy's default order; root `helper.h::gT` must agree with it and the saved `Nx/Ny/Nz`.
- Opening detection assumes cuts parallel to coordinate planes. Do not infer general geometry support from the directory name or commented alternative algorithm.
