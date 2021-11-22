import starfile
import eulerangles
import numpy as np
import pandas as pd


def star2pose(star_file):
    star = starfile.read(star_file)
    positions = star['particles'][[f'rlnCoordinate{ax}' for ax in 'XYZ']] \
        .to_numpy()
    shifts_angstroms = star['particles'][[f'rlnOrigin{ax}Angst' for ax in
                                          'XYZ']].to_numpy()
    pixel_sizes = star['particles']['rlnPixelSize'].to_numpy()
    shifts = shifts_angstroms / pixel_sizes[:, np.newaxis]
    positions -= shifts
    eulers = star['particles'][[f'rlnAngle{e}' for e in ('Rot', 'Tilt',
                                                         'Psi')]].to_numpy()
    orientations = eulerangles.euler2matrix(
        eulers,
        axes='zyz',
        intrinsic=True,
        right_handed_rotation=True
    ).swapaxes(-1, -2)
    sources = star['particles']['rlnMicrographName'].to_numpy()
    return positions, orientations, sources


def pose2star(poses, micrograph_names, star_file):
    eulers = eulerangles.matrix2euler(
        poses.orientations.swapaxes(-1, -2),
        axes='zyz',
        intrinsic=True,
        right_handed_rotation=True,
    )
    star_data = {
        'rlnCoordinateX': poses.positions[:, 0],
        'rlnCoordinateY': poses.positions[:, 1],
        'rlnCoordinateZ': poses.positions[:, 2],
        'rlnAngleRot': eulers[:, 0],
        'rlnAngleTilt': eulers[:, 1],
        'rlnAnglePsi': eulers[:, 2],
        'rlnMicrographName': np.asarray(micrograph_names),
    }
    for k, v in star_data.items():
        star_data[k] = v.reshape(-1)
    star_df = pd.DataFrame.from_dict(star_data)
    starfile.write(star_df, star_file, overwrite=True)


def read_transformations(subparticle_transformations):
    transformations = starfile.read(subparticle_transformations)
    shifts = transformations[[f'subboxerShift{ax}' for ax in 'XYZ']]
    eulers = transformations[[f'subboxerAngle{ax}' for ax in ('Rot', 'Tilt', 'Psi')]]
    rotations = eulerangles.euler2matrix(
        eulers,
        axes='zyz',
        intrinsic=True,
        right_handed_rotation=True
    ).swapaxes(-1, -2)
    return shifts, rotations