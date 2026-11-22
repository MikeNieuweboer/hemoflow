# Current geometry preprocessor

[Repository index](../AGENTS-docs.md) · [Legacy pipeline](../preprocessor/AGENTS-docs.md)

Run from the repository root: `python preprocessorlbm_versatile/main.py /path/to/input.config`. This directory uses bare sibling imports, not a Python package shared with `preprocessor/`.

## Flow and dependencies

1. `main.py` reads JSON; `geometry_dir` locates STL/VTP inputs and resolves the output prefix. Required keys and units are documented in [AGENTS.md](../AGENTS.md).
   The CLI accepts only the config path and `--debug`; JSON options `si_factor`, `cut_width`, and `distance` default to `0.001`, `1`, and `4`, respectively.
2. `voxelizeStl.py` uses numpy-stl → `slice.py` triangle intersections → `perimeter.py` rasterization; `util.py` pads the result. Internal slice order is rearranged to `(x,y,z)` before return.
3. `readCL.py` uses VTK to extract endpoint radii, centers, and tangents, then converts positions to voxel space. `main.py` derives boundary cuts and calls `createFluidSolid.py` to paint walls/fluid.
4. `detectOpenings.py` groups and paints openings using `constants.py`; `main.py` matches centers to centerline endpoints, then saves metadata and geometry separately.
5. The root solver reads `*ops.npz` and `*gf.h5`. Label changes also affect root `globals.h`, `hemoFlow.cpp`, and `opening.cpp`.

Dependencies: NumPy, numpy-stl, VTK, h5py; pynrrd for debug output. The commented connected-component alternative would additionally use SciPy, but is not active.

Function signatures use concrete lists/tuples for geometry and opening data, explicit `Generator` return types for functions using `yield`, and plain `np.ndarray` for NumPy arrays (no shape or dtype constraints).

## Files

| File | Responsibility |
| --- | --- |
| `config.template.json` | Copyable JSON configuration template containing required input/output fields and optional preprocessing settings with their defaults. |
| `main.py` | Pipeline/JSON entrypoint. Writes `output_base_name + "ops.npz"` with opening arrays, `dx`, dimensions, and an empty `stent` array; writes `output_base_name + "gf.h5"` with gzip-compressed flattened int8 `geometryFlag`. Stent paths are parsed but no stent voxelization runs here. |
| `voxelizeStl.py` | STL loading, scale/shift, slice rendering, padding, and axis swaps. Explicitly sets multiprocessing to `fork` inside `voxelize()` and uses 16 workers; repeated calls in one process can fail when resetting the start method. |
| `slice.py` | Triangle/plane intersections, interpolation, bounding-box-based target resolution, transforms, and axis swaps. Imports `perimeter.py` and distance/deduplication helpers from `util.py`. |
| `perimeter.py` | Converts slice line segments to filled or shell voxel planes; line selection/intersection helpers. NumPy-based, called by the voxelizer. |
| `util.py` | Array padding, point deduplication, Manhattan distance, and array/pixel inspection helpers used by voxelization/slicing. |
| `readCL.py` | VTP reader requiring `MaximumInscribedSphereRadius`. `inlet_line_ids = [4,5,6,7]` and first-line inlet handling control tangent signs for this specific centerline. |
| `createFluidSolid.py` | Zero-padded neighbor shifts expand the fluid mask into wall cells, trim empty bounds, and cut chosen domain faces. Returns int8 geometry plus crop bounds; imports multiprocessing but the wall calculation is serial. |
| `detectOpenings.py` | Active method scans surface voxels and recursively groups plane-aligned openings; connected-component code is commented out. `paint_dic` maps discovery order to named inlet/outlet labels. `detectOpenings()` currently discards its padded copy and slices one layer off the final result; check dimensions/centers when changing padding. |
| `constants.py` | Unused/wall/fluid labels 0/1/2, inlets 10–14, outlets 15–18. Must match root `globals.h`; old README flag tables do not apply. |
| `README.md` | Inherited usage/geometry notes; single-inlet assumptions and flag table are stale for this variant. |
| `run.sh` | Obsolete multi-positional-argument example; does not match `main.py`'s single JSON-config argument. |
| `test.py` | Manual comparison of opening tangents from absolute-path external NPZ files, with commented mutation examples; no assertions or portable test fixture. |
| `check.ipynb` | Ad hoc NumPy inspection of local `voxels.npy`, including a NaN check; no pipeline integration. |
| `AGENTS-docs.md` | This pipeline/file index. |

## Cross-file constraints

- NPZ opening arrays must stay in the same matched order; radii and `dx` are converted to meters using `SI_FACTOR = 0.001`, but centers remain voxel coordinates.
- Geometry is flattened with NumPy's default order; root `helper.h::gT` must agree with it and the saved `Nx/Ny/Nz`.
- Opening detection assumes cuts parallel to coordinate planes. Do not infer general geometry support from the directory name or commented alternative algorithm.
