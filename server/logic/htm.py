from enum import Enum
import math
import numba
import numpy as np
import sys
import typing

from .constants import EARTH_RADIUS

coordinates_type = typing.Tuple[float, float, float]
triangle_type = typing.Tuple[coordinates_type, coordinates_type, coordinates_type]

EPSILON = sys.float_info.epsilon


@numba.njit
def lat_lon_to_xyz(lat: float, lon: float) -> coordinates_type:
    """
    Returns the xyz coordinates of a point on the unit sphere
    """

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    x = math.cos(lat_rad) * math.cos(lon_rad)
    y = math.cos(lat_rad) * math.sin(lon_rad)
    z = math.sin(lat_rad)
    return x, y, z


def xyz_to_lat_lon(x: float, y: float, z: float) -> typing.Tuple[float, float]:
    """
    Returns the lat lon of a point on the unit sphere
    """

    lat_rad = math.asin(z)
    lon_rad = math.atan2(y, x)
    lat = math.degrees(lat_rad)
    lon = math.degrees(lon_rad)
    return lat, lon


@numba.njit
def midpoint_xyz(xyz1: coordinates_type, xyz2: coordinates_type) -> coordinates_type:
    """
    Returns the xyz coordinates of the midpoint of two points on a sphere
    """

    v1 = np.array(xyz1)
    v2 = np.array(xyz2)

    v = v1 + v2
    v = v / np.linalg.norm(v)

    return v[0], v[1], v[2]


def angle_between_np_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Returns the angle between two numpy vectors
    """

    val = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    clamped = max(-1.0, min(1.0, val))
    return math.acos(clamped)


class Halfspace:
    def __init__(self, vector: coordinates_type, distance: float):
        self.vector: coordinates_type = vector
        self.distance: float = distance

    def __str__(self):
        return f"Halfspace({self.vector}, {self.distance})"

    def arcangle(self):
        return math.acos(self.distance)

    def get_all_trixels_to_depth(self, depth: int) -> typing.List["Trixel"]:
        """
        Returns all trixels that intersect the halfspace up to the given depth, but does not expand any trixels

        If called with depth=10 and a trixel at depth=3 is fully inside, it will just return the trixel at depth=3 and not expand it
        """

        if depth < 1:
            raise ValueError("depth must be greater or equal to 1")

        candidates = []
        selected = []

        for trixel in octahedron.values():
            intersection = trixel.intersects_halfspace(self)

            if intersection == HalfspaceIntersection.FULL:
                selected.append(trixel)
            elif intersection == HalfspaceIntersection.PARTIAL:
                candidates.append(trixel)

        for i in range(depth - 1):
            new_candidates = []

            for candidate in candidates:
                subtrixels = candidate.get_subtrixels()

                for subtrixel in subtrixels:
                    intersection = subtrixel.intersects_halfspace(self)

                    if intersection == HalfspaceIntersection.FULL:
                        selected.append(subtrixel)
                    elif intersection == HalfspaceIntersection.PARTIAL:
                        new_candidates.append(subtrixel)

            candidates = new_candidates

        return selected + candidates

    def get_all_expanded_trixels_to_depth(self, depth: int) -> typing.List["Trixel"]:
        """
        Returns all trixels that intersect the halfspace up to the given depth and expands all trixels to the given depth
        """

        trixels = self.get_all_trixels_to_depth(depth)

        expanded_trixels = []

        for trixel in trixels:
            if trixel.depth() == depth:
                expanded_trixels.append(trixel)
            else:
                expanded_trixels.extend(trixel.get_subtrixels_at_depth(depth))

        return expanded_trixels


class HalfspaceIntersection(Enum):
    OUTSIDE = 0
    PARTIAL = 1
    FULL = 2


class Trixel:
    def __init__(self, name: str, vertices: triangle_type):
        self.name: str = name
        self.vertices: triangle_type = vertices

    def __str__(self):
        return f"{self.name}: {self.vertices}"

    def __repr__(self):
        return f"{self.name}: {self.vertices}"

    def serialize(self):
        return {
            "name": self.name,
            "vertices": self.vertices,
        }

    def lat_lon(self):
        """
        Latitude/longitude representation of the trixel
        """

        return {
            "name": self.name,
            "vertices": [xyz_to_lat_lon(*v) for v in self.vertices],
        }

    def depth(self):
        """
        Returns the depth of the trixel
        """

        return len(self.name.split("-"))

    def contains(self, x, y, z):
        """
        Returns whether the given point is contained in the trixel
        """
        return self.numba_contains(self.vertices[:3], x, y, z)

    @staticmethod
    @numba.njit
    def numba_contains(vert, x, y, z):
        p = np.array([x, y, z])

        # float64 precision works for at least all trixels up to depth 20
        if np.dot(np.cross(vert[0], vert[1]), p) < -EPSILON:
            return False

        if np.dot(np.cross(vert[1], vert[2]), p) < -EPSILON:
            return False

        if np.dot(np.cross(vert[2], vert[0]), p) < -EPSILON:
            return False

        return True

    def get_midpoint(self) -> coordinates_type:
        """
        Returns the xyz coordinates of the midpoint of the trixel
        """

        v0 = np.array(self.vertices[0])
        v1 = np.array(self.vertices[1])
        v2 = np.array(self.vertices[2])

        v = v0 + v1 + v2
        v = v / np.linalg.norm(v)

        return v[0], v[1], v[2]

    def get_subtrixels(self) -> typing.Generator["Trixel", None, None]:
        """
        Returns the four subtrixels of the trixel
        """

        v0, v1, v2 = self.vertices
        name = self.name

        w0 = midpoint_xyz(v1, v2)
        w1 = midpoint_xyz(v2, v0)
        w2 = midpoint_xyz(v0, v1)

        yield Trixel(name + "-0", (v0, w2, w1))  # t0
        yield Trixel(name + "-1", (v1, w0, w2))  # t1
        yield Trixel(name + "-2", (v2, w1, w0))  # t2
        yield Trixel(name + "-3", (w0, w1, w2))  # t3

        return

    def get_subtrixels_at_depth(self, depth: int) -> typing.List["Trixel"]:
        """
        Returns all subtrixels of the trixel at the given depth
        """

        if depth < 1:
            raise ValueError("depth must be greater or equal to 1")

        self_depth = self.depth()

        if self_depth == depth:
            return [self]

        if self_depth > depth:
            raise ValueError("depth must be greater than current depth")

        subtrixels = list(self.get_subtrixels())

        for i in range(depth - self_depth - 1):
            new_subtrixels = []

            for subtrixel in subtrixels:
                new_subtrixels.extend(list(subtrixel.get_subtrixels()))

            subtrixels = new_subtrixels

        return subtrixels

    def intersects_halfspace(self, halfspace: Halfspace) -> HalfspaceIntersection:
        """
        Returns whether the trixel intersects the given halfspace
        """

        v = np.array(halfspace.vector)
        d = halfspace.distance

        epsilon = sys.float_info.epsilon

        v0 = np.array(self.vertices[0])
        v1 = np.array(self.vertices[1])
        v2 = np.array(self.vertices[2])

        v0_inside = np.dot(v, v0) > d
        v1_inside = np.dot(v, v1) > d
        v2_inside = np.dot(v, v2) > d

        # all corners inside?
        if v0_inside and v1_inside and v2_inside:
            return HalfspaceIntersection.FULL

        # some corners inside?
        if v0_inside or v1_inside or v2_inside:
            return HalfspaceIntersection.PARTIAL

        v_bounding = np.cross(v1 - v0, v2 - v1)
        v_bounding = v_bounding / np.linalg.norm(v_bounding)

        d_bounding = np.dot(v0, v_bounding)

        bounding = Halfspace(v_bounding.tolist(), d_bounding)

        theta_bounding = angle_between_np_vectors(v, v_bounding)

        arcangle_sum = halfspace.arcangle() + bounding.arcangle()

        # bounding circle not intersecting halfspace?
        if theta_bounding >= arcangle_sum:
            return HalfspaceIntersection.OUTSIDE

        # halfspace intersects triangle side?
        for v_i, v_j in [(v0, v1), (v1, v2), (v2, v0)]:
            theta_ij = angle_between_np_vectors(v_i, v_j)

            u = math.tan(theta_ij / 2)

            gamma_i = np.dot(v, v_i)
            gamma_j = np.dot(v, v_j)

            # formula: -(u^2) * (gamma_i + d) * s^2 + (gamma_i * (u^2 - 1) + gamma_j * (u^2 + 1)) * s + gamma_i - d = 0
            # solve for s

            a = -(u**2) * (gamma_i + d)
            b = gamma_i * (u**2 - 1) + gamma_j * (u**2 + 1)
            c = gamma_i - d

            solutions = np.roots([a, b, c])

            for s in solutions:
                if 0 <= s <= 1:
                    return HalfspaceIntersection.PARTIAL

        # halfspace fully outside triangle?
        for v_i, v_j in [(v0, v1), (v1, v2), (v2, v0)]:
            if np.dot(np.cross(v_i, v_j), v) < -epsilon:
                return HalfspaceIntersection.OUTSIDE

        # halfspace is fully inside triangle
        return HalfspaceIntersection.PARTIAL


octahedron_vertices = (
    (0.0, 0.0, 1.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (-1.0, 0.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, -1.0),
)

octahedron: typing.Dict[str, Trixel] = {
    "N0": Trixel(
        "N0", (octahedron_vertices[1], octahedron_vertices[0], octahedron_vertices[4])
    ),
    "N1": Trixel(
        "N1", (octahedron_vertices[4], octahedron_vertices[0], octahedron_vertices[3])
    ),
    "N2": Trixel(
        "N2", (octahedron_vertices[3], octahedron_vertices[0], octahedron_vertices[2])
    ),
    "N3": Trixel(
        "N3", (octahedron_vertices[2], octahedron_vertices[0], octahedron_vertices[1])
    ),
    "S0": Trixel(
        "S0", (octahedron_vertices[1], octahedron_vertices[5], octahedron_vertices[2])
    ),
    "S1": Trixel(
        "S1", (octahedron_vertices[2], octahedron_vertices[5], octahedron_vertices[3])
    ),
    "S2": Trixel(
        "S2", (octahedron_vertices[3], octahedron_vertices[5], octahedron_vertices[4])
    ),
    "S3": Trixel(
        "S3", (octahedron_vertices[4], octahedron_vertices[5], octahedron_vertices[1])
    ),
}


def find_octahedron_trixel_from_xyz(x: float, y: float, z: float) -> Trixel:
    """
    Returns the trixel on the original octahedron that contains the point
    """

    if z > 0:
        if y > 0:
            if x > 0:
                return octahedron["N3"]
            else:
                return octahedron["N2"]
        else:
            if x > 0:
                return octahedron["N0"]
            else:
                return octahedron["N1"]
    else:
        if y > 0:
            if x > 0:
                return octahedron["S0"]
            else:
                return octahedron["S1"]
        else:
            if x > 0:
                return octahedron["S3"]
            else:
                return octahedron["S2"]


def find_trixel_from_xyz(x: float, y: float, z: float, depth: int) -> Trixel:
    """
    Returns the trixel at the given depth that contains the point
    """

    if depth < 1:
        raise ValueError("depth must be greater or equal to 1")

    octahedron_trixel = find_octahedron_trixel_from_xyz(x, y, z)

    if depth == 1:
        return octahedron_trixel

    trixel = octahedron_trixel

    def get_next(trixel, x, y, z):
        for t in trixel.get_subtrixels():
            if t.contains(x, y, z):
                return t

        raise ValueError(f"point not contained in any trixel (depth={depth}, i={i})")

    for i in range(depth - 1):
        trixel = get_next(trixel, x, y, z)

    return trixel


def find_trixel_from_lat_lon(lat: float, lon: float, depth: int) -> Trixel:
    """
    Returns the trixel at the given depth that contains the lat/lon point
    """

    xyz = lat_lon_to_xyz(lat, lon)
    return find_trixel_from_xyz(xyz[0], xyz[1], xyz[2], depth)


def find_trixel_from_name(name: str) -> Trixel:
    """
    Returns the trixel with the given name
    """

    path = name.split("-")

    if len(path) < 1:
        raise ValueError("invalid name")

    if path[0] not in octahedron:
        raise ValueError("invalid name")

    trixel = octahedron[path[0]]

    if len(path) == 1:
        return trixel

    for i in range(1, len(path)):
        t0, t1, t2, t3 = list(trixel.get_subtrixels())

        if path[i] == "0":
            trixel = t0
        elif path[i] == "1":
            trixel = t1
        elif path[i] == "2":
            trixel = t2
        elif path[i] == "3":
            trixel = t3
        else:
            raise ValueError("invalid name")

    return trixel


def get_all_trixels(depth: int) -> typing.List[typing.List[Trixel]]:
    """
    Returns all trixels up to the given depth
    """

    if depth < 1:
        raise ValueError("depth must be greater or equal to 1")

    trixels = [list(octahedron.values())]

    for i in range(depth - 1):
        new_trixels = []

        for trixel in trixels[-1]:
            new_trixels.extend(list(trixel.get_subtrixels()))

        trixels.append(new_trixels)

    return trixels


def get_all_trixels_serialized(depth: int) -> typing.List[typing.List[dict]]:
    return [
        [trixel.serialize() for trixel in layer] for layer in get_all_trixels(depth)
    ]


def get_all_trixels_lat_lon(depth: int) -> typing.List[typing.List[dict]]:
    return [[trixel.lat_lon() for trixel in layer] for layer in get_all_trixels(depth)]


def get_avg_trixel_area(depth: int) -> float:
    # for unit sphere: pi / (2 * 4^(depth - 1))
    return math.pi * EARTH_RADIUS**2 / (2 * 4 ** (depth - 1))


def get_min_trixel_side_length(depth: int) -> float:
    # for unit sphere: pi / (2^depth)
    return math.pi * EARTH_RADIUS / (2**depth)


def sphere_surface_radius_to_angle(distance: float) -> float:
    return distance / EARTH_RADIUS


def angle_to_halfspace_distance(angle: float) -> float:
    return math.cos(angle)


def sphere_surface_radius_to_halfspace_distance(distance: float) -> float:
    return angle_to_halfspace_distance(sphere_surface_radius_to_angle(distance))
