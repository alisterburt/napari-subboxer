from typing import Optional

import napari
import napari.layers
import numpy as np

from napari.utils.geometry import project_point_onto_plane


def point_in_bounding_box(point: np.ndarray, bounding_box: np.ndarray) -> bool:
    """Determine whether an nD point is inside an nD bounding box.
    Parameters
    ----------
    point : np.ndarray
        (n,) array containing nD point coordinates to check.
    bounding_box : np.ndarray
        (2, n) array containing the min and max of the nD bounding box.
        As returned by `Layer._extent_data`.
    """
    if np.all(point > bounding_box[0]) and np.all(point < bounding_box[1]):
        return True
    return False


def drag_data_to_projected_distance(
        start_position, end_position, view_direction, vector
):
    """Calculate the projected distance between two mouse events.
    Project the drag vector between two mouse events onto a 3D vector
    specified in data coordinates.
    The general strategy is to
    1) find mouse drag start and end positions, project them onto a
       pseudo-canvas (a plane aligned with the canvas) in data coordinates.
    2) project the mouse drag vector onto the (normalised) vector in data
       coordinates
    Parameters
    ----------
    start_position : np.ndarray
        Starting point of the drag vector in data coordinates
    end_position : np.ndarray
        End point of the drag vector in data coordinates
    view_direction : np.ndarray
        Vector defining the plane normal of the plane onto which the drag
        vector is projected.
    vector : np.ndarray
        (3,) unit vector or (n, 3) array thereof on which to project the drag
        vector from start_event to end_event. This argument is defined in data
        coordinates.
    Returns
    -------
    projected_distance : (1, ) or (n, ) np.ndarray of float
    """
    # enforce at least 2d input
    vector = np.atleast_2d(vector)

    # Store the start and end positions in world coordinates
    start_position = np.array(start_position)
    end_position = np.array(end_position)

    # Project the start and end positions onto a pseudo-canvas, a plane
    # parallel to the rendered canvas in data coordinates.
    start_position_canvas = start_position
    end_position_canvas = project_point_onto_plane(
        end_position, start_position_canvas, view_direction
    )
    # Calculate the drag vector on the pseudo-canvas.
    drag_vector_canvas = np.squeeze(
        end_position_canvas - start_position_canvas
    )

    # Project the drag vector onto the specified vector(s), return the distance
    return np.einsum('j, ij -> i', drag_vector_canvas, vector).squeeze()


def point_in_layer_bounding_box(point, layer):
    bbox = layer._display_bounding_box(layer._dims_displayed).T
    if np.any(point < bbox[0]) or np.any(point > bbox[1]):
        return False
    else:
        return True


def rotation_matrices_to_align_vectors(a: np.ndarray, b: np.ndarray):
    """
    Find rotation matrices r such that r @ a = b

    Implementation designed to avoid trig calls, a and b must be normalised.
    based on https://iquilezles.org/www/articles/noacos/noacos.htm

    Parameters
    ----------
    a : np.ndarray
        (1 or n, 3) normalised vector(s) of length 3.
    b : np.ndarray
        (1 or n, 3) normalised vector(s) of length 3.

    Returns
    -------
    r : np.ndarray
        (3, 3) rotation matrix or (n, 3, 3) array thereof.
    """
    # setup
    a = a.reshape(-1, 3)
    b = b.reshape(-1, 3)
    n_vectors = a.shape[0]

    # cross product to find axis about which rotation should occur
    axis = np.cross(a, b, axis=1)
    # dot product equals cosine of angle between normalised vectors
    cos_angle = np.einsum('ij, ij -> i', a, b)
    # k is a constant which appears as a factor in the rotation matrix
    k = 1 / (1 + cos_angle)

    # construct rotation matrix
    r = np.empty((n_vectors, 3, 3))
    r[:, 0, 0] = (axis[:, 0] * axis[:, 0] * k) + cos_angle
    r[:, 0, 1] = (axis[:, 1] * axis[:, 0] * k) - axis[:, 2]
    r[:, 0, 2] = (axis[:, 2] * axis[:, 0] * k) + axis[:, 1]
    r[:, 1, 0] = (axis[:, 0] * axis[:, 1] * k) + axis[:, 2]
    r[:, 1, 1] = (axis[:, 1] * axis[:, 1] * k) + cos_angle
    r[:, 1, 2] = (axis[:, 2] * axis[:, 1] * k) - axis[:, 0]
    r[:, 2, 0] = (axis[:, 0] * axis[:, 2] * k) - axis[:, 1]
    r[:, 2, 1] = (axis[:, 1] * axis[:, 2] * k) + axis[:, 0]
    r[:, 2, 2] = (axis[:, 2] * axis[:, 2] * k) + cos_angle

    return r.squeeze()


def rotation_matrix_from_z_vector(z_vector: np.ndarray):
    return rotation_matrices_to_align_vectors(np.array([0, 0, 1]), z_vector)


def theta2rotz(theta: np.ndarray) -> np.ndarray:
    """
    Rz = [[c(t), -s(t), 0],
          [s(t),  c(t), 0],
          [   0,     0, 1]]
    """
    theta = np.deg2rad(np.asarray(theta).reshape(-1))
    rotation_matrices = np.zeros((theta.shape[0], 3, 3), dtype=float)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    rotation_matrices[:, 2, 2] = 1
    rotation_matrices[:, (0, 1), (0, 1)] = cos_theta[:, np.newaxis]
    rotation_matrices[:, 0, 1] = -sin_theta
    rotation_matrices[:, 1, 0] = sin_theta
    return rotation_matrices.squeeze()