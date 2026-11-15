# Legacy geometry preprocessor

[Repository index](../AGENTS-docs.md) · [Current pipeline](../preprocessorlbm_versatile/AGENTS-docs.md)

This is the older single-inlet pipeline. `python preprocessor/main.py /path/to/input.config` accepts one JSON config, not the arguments in `run.sh`. Its combined `*c.npz` output is not the current solver's split NPZ/HDF5 contract.

## Flow and dependencies

`main.py` → `voxelizeStl.py` → `slice.py` / `perimeter.py` / `util.py` creates the vessel mask; `readCL.py` supplies centerline endpoints/tangents; `createFluidSolid.py` adds walls and cuts faces; `detectOpenings.py` uses `constants.py` to paint openings. `main.py` then matches opening centers and optionally voxelizes/merges three stent projections before saving.

Inputs are resolved relative to the config's directory (unlike the current variant's `geometry_dir`). JSON uses `geometry_original_stl`, `centerline_vtp`, `output_base_name`, `target_elements`, and stent-related keys. NumPy, numpy-stl, and VTK are runtime dependencies; debug NRRD output uses pynrrd. Sibling modules are local copies, not imports from the current variant.

## Files

| File | Responsibility |
| --- | --- |
| `main.py` | JSON entrypoint, centerline matching, cut-list generation, optional stent processing, and combined compressed `*c.npz` writer. Saves `geometryFlag`, `dx`, opening metadata, and `stent`, without the current split format's dimensions/HDF5 file. |
| `voxelizeStl.py` | numpy-stl loading, transform/resolution setup, serial slice rendering, padding, and axis restoration to `(x,y,z)`. Supports shell projections for the legacy stent path. Parallel prototype is commented out. |
| `slice.py` | Triangle/plane intersection and rasterization support, scale/shift calculation, interpolation, and axis swaps; uses `perimeter.py` and `util.py`. |
| `perimeter.py` | Rasterizes slice segments into filled or shell planes using NumPy and line-intersection helpers. |
| `util.py` | Voxel padding, point-list deduplication, Manhattan distance, and inspection/pixel helpers used by slicing/voxelization. |
| `readCL.py` | VTK centerline reader; assumes lines start at one shared inlet and end at outlets. Reads `MaximumInscribedSphereRadius`; converts centers to voxel coordinates and normalizes tangents. |
| `createFluidSolid.py` | Builds wall/fluid labels through zero-padded shifts, removes unused bounds, and applies face cuts; returns geometry and crop bounds used to align the stent volume. |
| `detectOpenings.py` | Recursive plane-wise opening grouping. Largest opening becomes inlet, smallest remaining opening pressure outlet; other openings become velocity outlets. Pads input and removes padding from returned geometry. |
| `constants.py` | Legacy single-inlet label definitions consumed by `detectOpenings.py`; not the current multi-inlet constants. |
| `README.md` | Legacy geometry assumptions, dependencies, and flag table; relevant here, not to current solver labels. |
| `run.sh` | Stale example using positional STL/output/resolution/cut/stent arguments; not compatible with the JSON entrypoint. |
| `AGENTS-docs.md` | This legacy pipeline/file index. |

Use `main.py` rather than assuming helper scripts' `__main__` blocks are maintained: `detectOpenings.py`'s standalone block unpacks two results from a function returning three, and `createFluidSolid.py`'s standalone writer receives the full return tuple.
