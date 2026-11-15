# Postprocessing notes

[Repository index](../AGENTS-docs.md)

| File | Responsibility and dependencies |
| --- | --- |
| `paraview_wss_calc.txt` | Manual ParaView recipe: convert data to a point set, sample on an STL surface, calculate normals, then use a Calculator expression to multiply the `PiNeq_XX/XY/XZ/YY/YZ/ZZ` tensor components by surface normals. Requires an STL surface and those named arrays; it is not an executable processing pipeline. |
| `AGENTS-docs.md` | This documentation index. |

The current `hemoFlow.cpp::writeHDF5` names its tensor output `sigma_1` through `sigma_6`, not `PiNeq_*`. Check the producing code and tensor component conventions before applying the historical expression to current output.
