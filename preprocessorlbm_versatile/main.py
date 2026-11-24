import argparse
import json
import logging
import sys
import time
from pathlib import Path

import git
import h5py
import numpy as np

from createFluidSolid import create_walls
from detectOpenings import detect_openings
from readCL import convert_to_voxelspace, get_openings_from_center_line
from voxelizeStl import voxelize

logger = logging.getLogger(__name__)


def in_range_3d(
    p_1: np.ndarray,
    p_2: tuple[float, float, float] | np.ndarray,
    distance: float | np.ndarray,
) -> bool | np.bool_:
    """Return True if two points are within manhattan distance of eachother."""
    if isinstance(distance, np.ndarray):
        return all(np.abs(p_1[i] - p_2[i]) < distance[i] for i in range(3))
    return all(np.abs(p_1[i] - p_2[i]) < distance for i in range(3))


def generate_cut_list(
    bounding_box: list[list[float]],
    radius_tangent_list: list[tuple[float, np.ndarray, np.ndarray]],
) -> np.ndarray:
    """Select faces within an endpoint radius using Manhattan distance.

    Bounds are [mins, maxs]; bounds, endpoints, and radii use geometry units.
    Face indices are x-min, x-max, y-min, y-max, z-min, z-max.
    """
    sides_to_cut = np.zeros(6, dtype=bool)
    bounds = np.asarray(bounding_box)

    logger.debug("Generating cutlist -> bounding box: %s", bounding_box)

    for radius, pos, _ in radius_tangent_list:
        logger.debug("Generating cutlist -> centerline point: %s", pos)

        for axis in range(3):
            for side in range(2):
                closest_point = np.clip(pos, bounds[0], bounds[1])
                closest_point[axis] = bounds[side, axis]
                distance = np.abs(pos - closest_point).sum()
                if distance <= radius:
                    sides_to_cut[axis * 2 + side] = True

    return np.flatnonzero(sides_to_cut)


def parse_arguments() -> argparse.Namespace:
    """Parse arguments required for preprocessing."""
    parser = argparse.ArgumentParser(
        description="Voxelize vessel geometry using a JSON configuration.",
    )
    parser.add_argument("config", type=Path, help="Path to the input JSON config file")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging and intermediate NRRD output",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Setup
    args = parse_arguments()
    DEBUG_MODE = args.debug

    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    if DEBUG_MODE:
        import nrrd

    conf_file: Path = args.config

    with conf_file.open() as json_file:
        conf_data: dict = json.load(json_file)

    SI_FACTOR = float(conf_data["si_factor"])
    cut_width = int(conf_data["cut_width"])

    root_dir = Path(git.Repo(".", search_parent_directories=True).git_dir).parent
    work_dir = root_dir / conf_data["geometry_dir"]

    geometry_path = work_dir / conf_data["geometry_original_stl"]
    center_line_file = work_dir / conf_data["centerline_vtp"]

    output_base_name = conf_data["output_base_name"]

    target_elem = int(conf_data["target_elements"])

    # Voxelizing stl
    start_time = time.time()

    logger.info("Voxelizing vessel geometry")
    voxel_vol, domain_data = voxelize(geometry_path, target_elem)
    print(type(voxel_vol))

    if DEBUG_MODE:
        logger.debug("Saving voxelization result")
        nrrd.write(str(work_dir / (output_base_name + "fluid_only.nrrd")), voxel_vol)

    scale = domain_data[0]
    shift = domain_data[1]
    bounding_box = domain_data[2]
    sx, sy, sz = scale
    tx, ty, tz = shift

    logger.info("Voxelized domain size: %s", voxel_vol.shape)
    logger.info("Bounding box: %s", bounding_box)
    logger.info("Transformation matrix from voxelization:")
    logger.info("Translate: %s %s %s", tz, tx, ty)
    logger.info("Rotate: %s %s %s", 90, 0, 90)
    logger.info("Scale: %s %s %s", sz, sx, sy)

    DX = (1.0 / sx) * SI_FACTOR
    logger.info("dx [m]: %s", DX)

    # TODO: Fix incorrect shift in centerlines due to padding and ob1.
    # Reading centerlines.
    logger.info("Extracting information on openings from centerline")
    radius_tangent_list = get_openings_from_center_line(center_line_file)
    radius_tangent_voxel_list = convert_to_voxelspace(
        radius_tangent_list,
        scale,
        shift,
    )

    cut_list = generate_cut_list(bounding_box, radius_tangent_list)

    logger.info("Computed list of sides to cut away for openings: %s", cut_list)

    # Creating walls.
    logger.info("Creating walls and opening in/outlets")
    start = time.time()
    vol_with_walls, _ = create_walls(voxel_vol, cut_list, cut_width)
    end = time.time()
    logger.info("Creating wall time: %s", end - start)

    if DEBUG_MODE:
        logger.debug("Saving nrrd wall geometry")
        nrrd.write(
            str(work_dir / (output_base_name + "wall_fluid.nrrd")), vol_with_walls
        )

    logger.info("Size after cutting layers for openings: %s", vol_with_walls.shape)
    volume = np.prod(vol_with_walls.shape)
    fluids = np.count_nonzero(vol_with_walls == 2)
    logger.info("Volume: %s", volume)
    logger.info("Fluid nodes: %s", fluids)
    logger.info("Fluid ratio: %s", fluids / volume)
    logger.info("Walls: %s", np.count_nonzero(vol_with_walls == 1))

    # Painting openings.
    logger.info("Detecting and assigning voxel openings")
    start = time.time()
    opening_ids, opening_centers, vol_painted = detect_openings(
        vol_with_walls,
    )
    end = time.time()
    logger.info("Detecting opening time: %s", end - start)

    if DEBUG_MODE:
        logger.debug("Saving nrrd painted geometry")
        nrrd.write(
            str(work_dir / (output_base_name + "vol_painted.nrrd")),
            vol_painted,
        )

    # TODO: Assign tangents and radii to voxelized openings

    if len(opening_centers) != len(radius_tangent_voxel_list):
        logger.error(
            "The number of outlets found on the voxelized domain sides differs "
            "from the number found along the centerline: centerline=%s, voxelized=%s",
            len(radius_tangent_voxel_list),
            len(opening_centers),
        )
        sys.exit(-1)

    # The combined information about openings in the correct order
    # (Inlet, Pressure outlet, Other velocity outlets)
    opening_radius = []
    opening_normalized_qratio = []
    opening_tangents = []

    # Radial ratio of outlets, note: Qinlet = 1, so it is not included
    r3_tot = np.sum([x[0] ** 3 for x in radius_tangent_voxel_list[1:]])

    for opening_i in range(len(opening_centers)):
        for radius, cl_endpoint, cl_tangent in radius_tangent_voxel_list:
            opening_center = opening_centers[opening_i]

            if (
                in_range_3d(opening_center, cl_endpoint, np.array(scale) * radius)
                is True
            ):
                opening_radius.append(radius * SI_FACTOR)
                opening_normalized_qratio.append(
                    radius**3 / r3_tot,
                )
                # TODO: it also assigns a number to the inlet, disregard that
                # TODO: Understand the previous todo.
                opening_tangents.append(np.array(cl_tangent))

    if len(opening_ids) != len(opening_centers):
        logger.debug(
            "Number of matched openings is incorrect: %s instead of %s",
            len(opening_ids),
            len(opening_centers),
        )

    logger.info("Saving final output")
    logger.info("File: %s", work_dir / (output_base_name + "ops.npz"))

    np.savez_compressed(
        work_dir / (output_base_name + "ops.npz"),
        dx=np.array([DX]).astype(np.double, copy=False),
        openingIndex=np.array(opening_ids).astype(np.int8, copy=False),
        openingRadius=np.array(opening_radius).astype(np.double, copy=False),
        openingNormalizedQRatio=np.array(opening_normalized_qratio).astype(
            np.double,
            copy=False,
        ),
        openingCenter=np.array(opening_centers).astype(np.double, copy=False),
        openingTangent=np.array(opening_tangents).astype(np.double, copy=False),
        Nx=vol_painted.shape[0],
        Ny=vol_painted.shape[1],
        Nz=vol_painted.shape[2],
    )

    logger.info("Maximum geometry flag: %s", vol_painted.max())

    # Create an HDF5 file to save the geometry flag seperately
    with h5py.File(output_base_name + "gf.h5", "w") as f:
        # Create a dataset in the file and store the array
        dset = f.create_dataset(
            "geometryFlag",
            shape=vol_painted.flatten().shape,
            data=vol_painted.flatten().astype(np.int8),
            dtype=np.int8,
            compression="gzip",
            compression_opts=9,
        )

    end_time = time.time()
    time_elapsed = round(end_time - start_time)
    logger.info("Done -> Elapsed total time: %s [s]", time_elapsed)
