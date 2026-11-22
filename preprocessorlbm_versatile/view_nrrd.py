"""Interactive, label-colored 3D viewer for main.py's debug NRRD files."""

import argparse
from functools import partial
from pathlib import Path

import nrrd
import numpy as np
import pyvista as pv

from constants import VoxelType

# Keep colors stable even when a file contains only a subset of labels.
COLORS = {
    VoxelType.UNUSED_VOXEL: "#888888",
    VoxelType.WALL_VOXEL: "#b8c4d0",
    VoxelType.FLUID_VOXEL: "#56b4e9",
    VoxelType.INLET_SVC: "#e69f00",
    VoxelType.INLET_IVC: "#d55e00",
    VoxelType.INLET_RHV: "#cc79a7",
    VoxelType.INLET_MHV: "#f0e442",
    VoxelType.INLET_LHV: "#009e73",
    VoxelType.OUTLET_RPA: "#0072b2",
    VoxelType.OUTLET_LPA: "#785ef0",
    VoxelType.OUTLET_SIDE_V: "#fe6100",
    VoxelType.OUTLET_SIDE_P: "#dc267f",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="View preprocessing NRRD labels as colored 3D surfaces.",
        epilog="Dependencies: python -m pip install numpy pynrrd pyvista",
    )
    parser.add_argument("file", type=Path, help="Path to a debug .nrrd file")
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="Save the final view as an image",
    )
    parser.add_argument(
        "--off-screen",
        action="store_true",
        help="Render without a window (requires --screenshot and a VTK rendering backend)",
    )
    args = parser.parse_args()
    if args.off_screen and args.screenshot is None:
        parser.error("--off-screen requires --screenshot")
    return args


def set_visibility(actor, plotter, visible: bool) -> None:
    actor.SetVisibility(visible)
    plotter.render()


def set_opacity(actor, plotter, opacity: float) -> None:
    actor.GetProperty().SetOpacity(opacity)
    plotter.render()


def show_volume(args: argparse.Namespace) -> None:
    # Lazy imports keep --help available without visualization dependencies.

    # Match pynrrd's default write order in main.py; axes remain (x, y, z).
    volume, _ = nrrd.read(str(args.file), index_order="F")
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3D label volume, got shape {volume.shape}")
    if volume.size == 0:
        raise ValueError("The NRRD volume is empty")
    if not np.issubdtype(volume.dtype, np.number) or np.iscomplexobj(volume):
        raise ValueError("Voxel labels must be numeric integers")
    labels, counts = np.unique(volume, return_counts=True)
    if not np.all(np.isfinite(labels)) or not np.all(labels == np.floor(labels)):
        raise ValueError("Voxel labels must be finite integers")

    names = {int(member): member.name for member in VoxelType}
    plotter = pv.Plotter(
        off_screen=args.off_screen,
        window_size=(1400, max(800, 180 + 48 * len(labels))),
    )
    plotter.set_background("#20252b")
    plotter.add_text(
        f"{args.file.name}\n"
        "Checkbox: visibility | Slider: opacity\n"
        "Drag: rotate | Wheel: zoom | Shift-drag: pan",
        position="upper_left",
        font_size=10,
    )
    legend = []
    for row, (value, count) in enumerate(zip(labels, counts)):
        label = int(value)
        name = names.get(label, f"UNKNOWN_LABEL_{label}")
        color = COLORS.get(label, "#ffffff")
        print(f"{label:3d}  {name:20s} {int(count):12,d} voxels")

        # Treat labels as whole cells, not point samples for interpolation.
        # Cell centers remain at integer voxel indices; faces lie at +/- 0.5.
        grid = pv.ImageData(
            dimensions=tuple(size + 1 for size in volume.shape),
            origin=(-0.5, -0.5, -0.5),
        )
        grid.cell_data["label"] = (volume == value).ravel(order="F").astype(np.uint8)
        cells = grid.threshold(0.5, scalars="label", preference="cell")
        # Remove shared internal faces, keeping only exact axis-aligned quads.
        surface = cells.extract_surface()
        del grid, cells
        if surface.n_points == 0:
            continue
        opacity = 0.2 if label == VoxelType.WALL_VOXEL else 1.0
        actor = plotter.add_mesh(
            surface,
            color=color,
            opacity=opacity,
            smooth_shading=False,
            show_scalar_bar=False,
        )
        visible = label != VoxelType.UNUSED_VOXEL
        actor.SetVisibility(visible)
        legend.append([f"{label}: {name}", color])

        y_pixels = 35 + row * 48
        plotter.add_checkbox_button_widget(
            partial(set_visibility, actor, plotter),
            value=visible,
            position=(12, y_pixels),
            size=22,
            color_on=color,
            color_off="#555555",
            background_color="#20252b",
        )
        plotter.add_text(
            f"{label}: {name}",
            position=(45, y_pixels + 4),
            font_size=9,
            color=color,
            name=f"label-{label}",
        )
        y = (y_pixels + 12) / plotter.window_size[1]
        plotter.add_slider_widget(
            partial(set_opacity, actor, plotter),
            rng=(0.0, 1.0),
            value=opacity,
            pointa=(0.23, y),
            pointb=(0.36, y),
            title="",
            color=color,
            interaction_event="always",
        )

    plotter.add_legend(legend, bcolor="#20252b", size=(0.22, 0.32))
    plotter.add_axes()
    plotter.show_grid(
        xtitle="X (voxels)",
        ytitle="Y (voxels)",
        ztitle="Z (voxels)",
    )
    plotter.view_isometric()
    plotter.reset_camera()
    plotter.show(
        screenshot=str(args.screenshot) if args.screenshot is not None else None,
    )


def main() -> None:
    args = parse_arguments()
    try:
        show_volume(args)
    except ImportError as error:
        raise SystemExit(
            "Missing viewer dependency. Install with:\n"
            "  python -m pip install numpy pynrrd pyvista",
        ) from error
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot view {args.file}: {error}") from error


if __name__ == "__main__":
    main()
