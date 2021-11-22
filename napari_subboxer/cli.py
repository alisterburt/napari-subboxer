from pathlib import Path

import eulerangles
import napari
import numpy as np
import starfile
import typer

from .pose_io import pose2star, star2pose, read_transformations
from .eralda import Pose, Transform
cli = typer.Typer()


@cli.command()
def define(map_file: Path = typer.Argument(
    None,
    exists=True,
    file_okay=True,
    readable=True,
)):
    """Define subparticle transformations using an interactive napari viewer.

    Controls:
    x/y/z - align plane normal along x/y/z axis
    click and drag plane - shift plane along its normal vector
    alt-click - add point on plane
    o - align plane normal to view direction
    [] - decrease/increase plane thickness
    """
    viewer = napari.Viewer()
    _, subboxing_widget = viewer.window.add_plugin_dock_widget(
        plugin_name='napari-subboxer'
    )
    if map_file is not None:
        subboxing_widget.cli.open_map(map_file)
    napari.run()


@cli.command()
def apply(transformations: Path, poses: Path, output: Path):
    """Apply subparticle transformations on a set of poses from a consensus
    refinement.

    The poses being transformed should be the same as those which produced
    the map used to define
    """
    shifts, rotations = read_transformations(transformations)
    positions, orientations, sources = star2pose(poses)
    n_transformations = len(shifts)
    n_poses = len(positions)

    poses = Pose(positions=positions, orientations=orientations)
    transforms = Transform(shifts=shifts, rotations=rotations)
    transformed_positions, transformed_orientations = transforms.apply(poses)
    transformed_sources = np.broadcast_to(
        sources[np.newaxis, :], shape=(n_transformations, n_poses)
    ).reshape(-1)
    transformed_poses = Pose(
        positions=transformed_positions, orientations=transformed_orientations
    )
    pose2star(poses=transformed_poses, micrograph_names=transformed_sources,
              star_file=output)
