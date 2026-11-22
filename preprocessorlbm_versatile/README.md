# LBM_preprocess tools for HemoFlow

## Usage

```bash
python main.py /path/to/input.json [--debug]
```

Only the config path and optional `--debug` flag are command-line arguments.
Copy `config.template.json` and fill in your geometry paths and desired settings.
Set preprocessing parameters in the JSON config:

```json
{
  "geometry_dir": "/path/to/geometry",
  "geometry_original_stl": "vessel.stl",
  "centerline_vtp": "centerline.vtp",
  "output_base_name": "vessel_",
  "target_elements": 1000000,
  "si_factor": 0.001,
  "cut_width": 1,
  "distance": 4
}
```

The last three fields are optional:

| Field | Default | Meaning |
| --- | --- | --- |
| `si_factor` | `0.001` | Geometry unit conversion factor to meters (default assumes millimeters). |
| `cut_width` | `1` | Number of voxel layers to cut at openings. |
| `distance` | `4` | Voxel tolerance for boundary cuts and opening matching. |

Input: JSON config file
Output: voxelized geometry

Notes: 
- The nrrd output is saved since it can be opened in 3DSlicer to investigate the results of the voxelisation.
- The centerline must contain one line per outlet, with each line running from the inlet (source) to one outlet (target)
.
### Specify sides that should contain an opening.
This will practically cut away a layer of voxels from these sides.

Cutlist meaning -> cut one layer from the planes:
    # 0,1 => Xmin, Xmax
    # 2,3 => Ymin, Ymax
    # 4,5 => Zmin, Zmax

### Interactive NRRD viewer

View any of the `fluid_only.nrrd`, `wall_fluid.nrrd`, or `geometry.nrrd`
files written by `main.py --debug`:

```bash
python -m pip install numpy pynrrd pyvista
python view_nrrd.py /path/to/vessel_geometry.nrrd
```

Each voxel type from `constants.py` has a stable color and a named legend entry.
Use the bottom-left checkboxes to show/hide types and the adjacent sliders to
adjust opacity. Unused voxels start hidden; walls start translucent. Unknown
labels appear in white with their numeric identifier. Drag to rotate, scroll to
zoom, and Shift-drag to pan.

The surfaces consist of exposed, axis-aligned voxel cube faces, without
interpolation or smoothing. Internal faces between voxels of the same type are
omitted. Coordinates are voxel indices, not millimeters:
`main.py` does not write physical spacing/origin into its debug NRRDs.
Large volumes (especially the unused-region surface) can take time and memory
to load.

Use `--screenshot view.png` to save the final view, or
`--off-screen --screenshot view.png` to render without opening a window.
Off-screen rendering still requires a working VTK rendering backend.

### Preprocessor dependencies

Tested with Anaconda and Python 3.7

- pynrrd (PIP/conda-forge)
- numpy-stl (PIP/conda-forge)

### Known problems

- The triangle size cannot be smaller than the projected voxel size. I.e.: If you see walls appearing inside the fluid domain, or get complaints that the thing is not watertight (but you are sure it is), increase the resolution (also reduce the number of faces on the geometry?).

- The inlet and the pressure outlet are automatically detected as the largest and smallest are opening. Due to the various cut angles, this can be incorrect! Look for a better method based on centerline!

- Also automate the cutlist based on the centerline!

## Flag table

- 0 unused
- 1 wall
- 2 fluid
- 3 porous
- 10 inlet (velocity)
- 11 outlet 1 (pressure)
- 12... other outlets (velocity)
