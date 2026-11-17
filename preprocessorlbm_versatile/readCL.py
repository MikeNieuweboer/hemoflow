"""Created on Wed Aug  5 13:50:33 2020.

@author: gzavo
"""

from pathlib import Path

import numpy as np
import vtk


def get_id_list(vtk_id_list: vtk.vtkIdList) -> list[int]:
    """Retrieve a list of all ids in the vtkIdList."""
    return [vtk_id_list.GetId(i) for i in range(vtk_id_list.GetNumberOfIds())]


def normalize(v: np.ndarray) -> np.ndarray:
    """Normalize a 3D array.

    Returns
    -------
    The normalized array, or a zero array if the magnitude is 0.

    """
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def get_openings_from_center_line(
    file_path: Path,
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    """
    Parameters
    ----------
    file_name: Path
        Name of the centerline file (VTP).

    Returns
    -------
    We'll see. But we assume all centerline runs from source (inlet) to target.

    """
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(file_path.name)
    reader.Update()

    data: vtk.vtkPolyData = reader.GetOutput()
    points = data.GetPoints()
    point_data = data.GetPointData()
    radius_data = point_data.GetArray("MaximumInscribedSphereRadius")

    # Read the number of lines in the dataset
    n_lines = data.GetNumberOfLines()

    r_tan_data = []

    # TODO:
    # inlet line ids. Note, only is correct with the current centerline file !!!!!!!!
    # How did I know? Hardcoded...... dumb but useful, need to find a portable way
    # VMTK has some problems with multiple inlets geometry, therefore need to hardcode
    inlet_line_ids = [4, 5, 6, 7]  # and unlabelled inlet
    for ll in range(n_lines):
        line = data.GetCell(ll)

        # Get the IDs of the datapoints on the selected line
        id_list = get_id_list(line.GetPointIds())

        # Get radii on the selected line
        r_array = np.array([radius_data.GetTuple(i)[0] for i in id_list])

        # Get points on the selected line
        p_array = [np.array(points.GetPoint(i)) for i in id_list]

        r1 = r_array[0]
        r2 = r_array[-1]

        if ll == 0:  # The first inlet!
            v1 = p_array[0] - p_array[1]
            r_tan_data.append((r1, p_array[0], -v1))  # The inlet should point inwards

        # Note, the last 2 points are sometimes the same for some reason
        v2 = p_array[-1] - p_array[-3]

        # Inlet! point inwards!
        if ll in (inlet_line_ids):
            r_tan_data.append((r2, p_array[-1], -v2))
        # All other tangents are pointing outwards
        else:
            r_tan_data.append((r2, p_array[-1], v2))

    return r_tan_data


def convert_to_voxelspace(
    r_tan_data: list[tuple[float, np.ndarray, np.ndarray]],
    scale: list[float],
    shift: list[float],
) -> list[tuple[float, np.ndarray, np.ndarray]]:
    voxel_list = []
    for opening in r_tan_data:
        r, pos, tan = opening
        newpos = (pos + shift) * scale
        voxel_list.append((r, newpos, normalize(tan)))

    return voxel_list
