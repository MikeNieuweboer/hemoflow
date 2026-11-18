import argparse
import json
import logging
import sys
import time
from pathlib import Path

import h5py
import numpy as np

from createFluidSolid import create_walls
from detectOpenings import detect_openings
from readCL import convert_to_voxelspace, get_openings_from_center_line
from voxelizeStl import voxelize

logger = logging.getLogger(__name__)


def in_range(x: float, y: float, distance: float) -> bool:
    """Check whether x and y are at most distance away from eachother."""
    return np.abs(y - x) < distance


def in_range_3d(
    value_3d: np.ndarray,
    range_value_3d: tuple[float, float, float],
    distance: int,
) -> bool | np.bool_:
    is_in_range = True
    for i in range(3):
        is_in_range = is_in_range and in_range(value_3d[i], range_value_3d[i], distance)

    return is_in_range


def generate_cut_list(
    voxel_domain_size: list[int],
    radius_tangent_voxel_list: list[tuple[float, np.ndarray, np.ndarray]],
    distance: int = 4,
) -> np.ndarray:
    sides_to_cut = np.zeros(6)

    # If centerline point is within this distance of the boundary it is
    # considered an opening Cutting away unused layers might influence this
    # distance.

    logger.debug("Generating cutlist -> voxelDomainSize: %s", voxel_domain_size)

    for o in radius_tangent_voxel_list:
        pos = o[1]

        logger.debug("Generating cutlist -> centerline point: %s", pos)

        for j in range(3):
            if in_range(pos[j], 0, distance):
                sides_to_cut[j * 2] = 1
            if in_range(pos[j], voxel_domain_size[j], distance):
                sides_to_cut[j * 2 + 1] = 1

    return np.where(sides_to_cut == 1)[0]

class Arguments(argparse.Namespace):
    """Class definition of input arguments."""

    config: Path
    debug: bool
    si_factor: float
    cut_width: int
    distance: int

def parse_arguments() -> Arguments:
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
    parser.add_argument(
        "--si-factor",
        type=float,
        default=0.001,
        help="Geometry unit conversion factor to meters (default: 0.001, millimeters)",
    )
    parser.add_argument(
        "--cut-width",
        type=int,
        default=1,
        help="Number of voxel layers to cut at openings (default: 1)",
    )
    parser.add_argument(
        "--distance",
        type=int,
        default=4,
        help="Voxel tolerance for boundary cuts and opening matching (default: 4)",
    )
    return parser.parse_args(namespace=Arguments())


if __name__ == "__main__":
    args = parse_arguments()
    DEBUG_MODE = args.debug
    SI_FACTOR = args.si_factor

    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    if DEBUG_MODE:
        import nrrd

    cut_width = args.cut_width
    distance = args.distance

    conf_file: Path = args.config
    save_dir = conf_file.parent

    with conf_file.open() as json_file:
        conf_data = json.load(json_file)

    work_dir = Path(conf_data["geometry_dir"])

    geometry_path = work_dir / conf_data["geometry_original_stl"]
    center_line_file = work_dir / conf_data["centerline_vtp"]

    output_base_name = save_dir / conf_data["output_base_name"]

    target_elem = int(conf_data["target_elements"])

    voxel_stent_final = np.zeros(0)

    start_time = time.time()

    logger.info("Voxelizing vessel geometry")
    voxel_vol, domain_data = voxelize(geometry_path, target_elem)

    if DEBUG_MODE:
        logger.debug("Saving voxelization result")
        nrrd.write(output_base_name + "fluid_only.nrrd", voxel_vol)

    scale = domain_data[0]
    shift = domain_data[1]
    domain = domain_data[2]
    bounding_box = domain_data[3]
    sx, sy, sz = scale
    tx, ty, tz = shift

    logger.info("Voxelized domain size: %s", voxel_vol.shape)
    logger.info("Domain: %s", domain)
    logger.info("Bounding box: %s", bounding_box)
    logger.info("Transformation matrix from voxelization:")
    logger.info("Translate: %s %s %s", tz, tx, ty)
    logger.info("Rotate: %s %s %s", 90, 0, 90)
    logger.info("Scale: %s %s %s", sz, sx, sy)

    DX = (1.0 / sx) * SI_FACTOR
    logger.info("dx [m]: %s", DX)

    logger.info("Extracting information on openings from centerline")
    radius_tangent_list = get_openings_from_center_line(center_line_file)
    logger.info("Scale: %s", scale)
    logger.info("Translate: %s", shift)
    radius_tangent_voxel_list = convert_to_voxelspace(
        radius_tangent_list,
        domain_data[0],
        domain_data[1],
    )

    cut_list = generate_cut_list(domain, radius_tangent_voxel_list, distance)

    logger.info("Computed list of sides to cut away for openings: %s", cut_list)

    logger.info("Creating walls and opening in/outlets")
    start = time.time()
    vol_with_walls, _ = create_walls(voxel_vol, cut_list, cut_width)
    end = time.time()
    logger.info("Creating wall time: %s", end - start)

    if DEBUG_MODE:
        logger.debug("Saving nrrd wall geometry")
        nrrd.write(output_base_name + "wall_fluid.nrrd", vol_with_walls)

    logger.info("Size after cutting layers for openings: %s", vol_with_walls.shape)
    volume = np.prod(vol_with_walls.shape)
    fluids = np.count_nonzero(vol_with_walls == 2)
    logger.info("Volume: %s", volume)
    logger.info("Fluid nodes: %s", fluids)
    logger.info("Fluid ratio: %s", fluids / volume)
    logger.info("Walls: %s", np.count_nonzero(vol_with_walls == 1))

    logger.info("Detecting and assigning voxel openings")
    start = time.time()
    opening_ids, opening_centers, Inlets_outlets_voxles, painted_openings = (
        detect_openings(vol_with_walls)
    )
    end = time.time()
    logger.info("Detecting opening time: %s", end - start)

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
    opening_index = []
    opening_radius = []
    opening_normalized_qratio = []
    opening_center = []
    opening_tangent = []

    # Radial ratio of outlets, note: Qinlet = 1, so it is not included
    r3_tot = np.sum([x[0] ** 3 for x in radius_tangent_voxel_list[1:]])

    for cc_vox in range(len(opening_centers)):
        for cc_cl in range(len(radius_tangent_voxel_list)):
            c_vox = opening_centers[cc_vox]
            r_cl = radius_tangent_voxel_list[cc_cl]
            c_cl = r_cl[1]

            if in_range_3d(c_vox, (c_cl[0], c_cl[1], c_cl[2]), distance) is True:
                opening_index.append(opening_ids[cc_vox])
                opening_radius.append(r_cl[0] * SI_FACTOR)
                opening_normalized_qratio.append(
                    r_cl[0] ** 3 / r3_tot,
                )  # TODO: it also assigns a number to the inlet, disredards that
                opening_center.append(c_vox)
                opening_tangent.append(np.array((r_cl[2][0], r_cl[2][1], r_cl[2][2])))

    if DEBUG_MODE:
        logger.debug("Saving nrrd geometry flag")
        nrrd.write(output_base_name + "geometry.nrrd", painted_openings)
        if len(opening_index) != len(opening_centers):
            logger.debug(
                "Number of matched openings is incorrect: %s instead of %s",
                len(opening_index),
                len(opening_centers),
            )

    logger.info("Saving final output")
    logger.info("File: %s", output_base_name + "ops.npz")

    np.savez_compressed(
        output_base_name + "ops.npz",
        dx=np.array([DX]).astype(np.double, copy=False),
        openingIndex=np.array(opening_index).astype(np.int8, copy=False),
        openingRadius=np.array(opening_radius).astype(np.double, copy=False),
        openingNormalizedQRatio=np.array(opening_normalized_qratio).astype(
            np.double,
            copy=False,
        ),
        openingCenter=np.array(opening_center).astype(np.double, copy=False),
        openingTangent=np.array(opening_tangent).astype(np.double, copy=False),
        stent=voxel_stent_final.astype(np.short, copy=False),
        Nx=painted_openings.shape[0],
        Ny=painted_openings.shape[1],
        Nz=painted_openings.shape[2],
    )

    logger.info("Maximum geometry flag: %s", painted_openings.max())

    # Create an HDF5 file to save the geometry flag seperately
    with h5py.File(output_base_name + "gf.h5", "w") as f:
        # Create a dataset in the file and store the array
        dset = f.create_dataset(
            "geometryFlag",
            shape=painted_openings.flatten().shape,
            data=painted_openings.flatten().astype(np.int8),
            dtype=np.int8,
            compression="gzip",
            compression_opts=9,
        )

    end_time = time.time()
    time_elapsed = round(end_time - start_time)
    logger.info("Done -> Elapsed total time: %s [s]", time_elapsed)
