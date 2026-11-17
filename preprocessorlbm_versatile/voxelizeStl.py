import functools
import multiprocessing
import time
from collections.abc import Generator
from pathlib import Path

import numpy as np
import stl

import perimeter
from geometry_types import Triangle
from slice import (
    calculate_scale_and_shift,
    scale_and_shift_mesh,
    swap_axis,
    to_intersecting_lines,
)
from util import pad_voxel_array, remove_dups_from_point_list


def voxelize(
    input_path: Path,
    target_elements: int,
    domain_data: tuple[
        list[float],
        list[float],
        list[int],
        list[list[float]],
    ]
    | None = None,
    rotation: int = -1,
    *,
    is_mesh_a_shell: bool = False,
) -> tuple[
    np.ndarray,
    tuple[
        list[float],
        list[float],
        list[int],
        list[list[float]],
    ],
]:
    mesh = list(import_stl_file(input_path))

    if domain_data is None:
        scale, shift, domain, bounding_box = calculate_scale_and_shift(
            mesh,
            target_elements,
        )
    else:
        scale, shift, domain, bounding_box = domain_data

    # Shift all points to Voxel dimensions, [0, domain]
    mesh = list(scale_and_shift_mesh(mesh, scale, shift))

    # If it is a shell mesh, rotate here for different projections!
    if rotation == 0:
        mesh = list(swap_axis(mesh, 0, 1))
        domain = [domain[1], domain[0], domain[2]]
    elif rotation == 1:
        mesh = list(swap_axis(mesh, 1, 2))
        domain = [domain[0], domain[2], domain[1]]

    start = time.time()

    # Parallel
    multiprocessing.set_start_method("fork")
    pool = multiprocessing.Pool(16)

    # Voxelize each layer in z-direction.
    vol = np.array(
        pool.map(
            functools.partial(
                render_slice,
                mesh=mesh,
                domain=domain,
                is_mesh_a_shell=is_mesh_a_shell,
            ),
            range(int(domain[2])),
        ),
    )

    pool.close()

    print(vol.shape)

    vol = pad_voxel_array(vol)
    domain = list(vol.shape)

    end = time.time()
    print(f"Voxelization time: {end - start}")

    # If it is a shell mesh, rotate back here the different projections!
    if rotation == 0:
        vol = np.swapaxes(vol, 1, 2)
    elif rotation == 1:
        vol = np.swapaxes(vol, 0, 2)

    # At the very end here fix the [z][x][y] back to [x][y][z]
    vol = np.swapaxes(vol, 0, 2)
    vol = np.swapaxes(vol, 0, 1)

    return (vol, (scale, shift, domain, bounding_box))


def render_slice(
    height: int,
    mesh: list[Triangle],
    domain: list[int],
    *,
    is_mesh_a_shell: bool = False,
) -> np.ndarray:
    """Create a voxelized slice of the mesh at the given height in voxel units."""
    lines = to_intersecting_lines(mesh, height)
    prepixel = np.zeros((domain[0], domain[1]), dtype=bool)
    perimeter.lines_to_voxels(lines, prepixel, is_shell=is_mesh_a_shell)
    return prepixel


def import_stl_file(
    input_path: Path,
) -> Generator[Triangle]:
    """Create a generator for the points of each triangle in the stl mesh."""
    imported_mesh = stl.mesh.Mesh.from_file(input_path.name)
    return get_stl_faces(imported_mesh)


def get_stl_faces(
    mesh: stl.mesh.Mesh,
) -> Generator[Triangle]:
    """Yield three valid points for each triangle."""
    for i, j, k in zip(mesh.v0, mesh.v1, mesh.v2, strict=True):
        v1, v2, v3 = tuple(i), tuple(j), tuple(k)
        corners = 3
        if len(remove_dups_from_point_list([v1, v2, v3])) == corners:
            yield (v1, v2, v3)
        else:
            pass


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage:", sys.argv[0], "input.nrrd output.nrrd targetElementNum")
        sys.exit(-1)

    from nrrd import write

    output_volume, domain_data = voxelize(sys.argv[1], int(sys.argv[3]))

    write(sys.argv[2], output_volume)
