"""
This module was developing using ChatGPT.

Generate valid square and rectangular geographic boundaries for Otter.

Supported boundary definitions:
    1. Square from top-left corner and side length.
    2. Square from center and circumradius.
    3. Rectangle from top-left and bottom-right corners.
    4. top_left + top_right + aspect_ratio

Coordinates supplied to and returned from this module use:
    (latitude, longitude)

Bearing:
    Degrees clockwise from true north.

Returned corner order:
    Top-left, top-right, bottom-right, bottom-left.

Optional exports:
    Point shapefile containing the four corners and center.
    Polygon shapefile containing the complete boundary.

The geographic coordinates returned by generate_boundary() are always
WGS84, regardless of the CRS selected for shapefile exports.


USAGE:
-------------------------------------------------
corners = generate_boundary(
    top_left=(37.7749, -122.4194),
    side_length=100,
    unit="km",
    bearing=45,
    point_shapefile="output/square_points.shp",
    polygon_shapefile="output/square_boundary.shp",
    output_crs="EPSG:4326",
)

# Pass directly to Otter
otter.bother(
    corners=corners,
    outfile="output/heightmap.png",
    outfile_tif="output/heightmap.tif",
    scale_image="2048x2048",
)


SQUARE FROM CENTER POINT

corners = generate_boundary(
    center=(37.7749, -122.4194),
    radius=50,
    unit="km",
    bearing=45,
    point_shapefile="output/center_square_points.shp",
    polygon_shapefile="output/center_square.shp",
)


RECTANGLE
corners = generate_boundary(
    top_left=(40.0, -125.0),
    bottom_right=(35.0, -115.0),
    bearing=45,
    unit="km",
    point_shapefile="output/rectangle_points.shp",
    polygon_shapefile="output/rectangle.shp",
    output_crs="EPSG:32610",
)


corners = otter.generate_boundary(
    top_left=(51.89922426, -85.79633351),
    top_right=(48.00000000, -75.00000000),
    aspect_ratio=(4, 3), # width, height
    point_shapefile="rectangle_points.shp",
    polygon_shapefile="rectangle_boundary.shp",
)

"""

import math
import os

import geopandas as gpd

from pyproj import CRS, Geod, Transformer
from pyproj.exceptions import CRSError

from shapely.geometry import Point, Polygon

from pathlib import Path

import warnings

# ---------------------------------------------------------------------------
# Distance unit conversions
# ---------------------------------------------------------------------------

UNIT_TO_METERS = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,

    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "kilometre": 1000.0,
    "kilometres": 1000.0,

    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "centimetre": 0.01,
    "centimetres": 0.01,

    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "millimetre": 0.001,
    "millimetres": 0.001,

    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,

    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,

    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,

    "nmi": 1852.0,
    "nautical_mile": 1852.0,
    "nautical_miles": 1852.0,
}


def _to_meters(value, unit):
    """Convert a supplied distance to meters."""

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("Distance must be a numeric value.")

    if not math.isfinite(value) or value <= 0:
        raise ValueError("Distance must be a positive, finite value.")

    unit = str(unit).lower().strip()

    if unit not in UNIT_TO_METERS:
        raise ValueError(
            f"Unsupported distance unit '{unit}'. "
            f"Supported units: {', '.join(UNIT_TO_METERS)}"
        )

    return float(value) * UNIT_TO_METERS[unit]


# ---------------------------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------------------------

def _validate_coordinate(coordinate, name):
    """Validate a latitude/longitude coordinate pair."""

    if not isinstance(coordinate, (list, tuple)):
        raise TypeError(f"{name} must be a (latitude, longitude) pair.")

    if len(coordinate) != 2:
        raise ValueError(f"{name} must contain exactly two values.")

    lat, lon = map(float, coordinate)

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError(f"{name} must contain finite coordinates.")

    if not -90 <= lat <= 90:
        raise ValueError(f"{name} has an invalid latitude.")

    if not -180 <= lon <= 180:
        raise ValueError(f"{name} has an invalid longitude.")

    return lat, lon


def _normalize_bearing(bearing):
    """Normalize bearing to the range 0-360 degrees."""

    bearing = float(bearing)

    if not math.isfinite(bearing):
        raise ValueError("Bearing must be finite.")

    return bearing % 360


def _validate_aspect_ratio(aspect_ratio):
    """
    Validate an OpenTTD-compatible map aspect ratio.

    Accepted ratios are powers of two, from 1:256 through 256:1.
    """
    if (
        not isinstance(aspect_ratio, (tuple, list))
        or len(aspect_ratio) != 2
    ):
        raise ValueError(
            "aspect_ratio must be a (width, height) tuple or list."
        )

    width, height = aspect_ratio

    if (
        isinstance(width, bool)
        or isinstance(height, bool)
        or not isinstance(width, (int, float))
        or not isinstance(height, (int, float))
        or not math.isfinite(width)
        or not math.isfinite(height)
        or width <= 0
        or height <= 0
    ):
        raise ValueError(
            "Aspect ratio dimensions must be positive, finite numbers."
        )

    ratio = width / height
    exponent = math.log2(ratio)
    nearest_exponent = round(exponent)

    if (
        nearest_exponent < -8
        or nearest_exponent > 8
        or not math.isclose(
            exponent,
            nearest_exponent,
            rel_tol=0,
            abs_tol=1e-9,
        )
    ):
        raise ValueError(
            "Unsupported aspect ratio. OpenTTD-compatible ratios "
            "must be powers of two between 1:256 and 256:1."
        )

    return ratio

# ---------------------------------------------------------------------------
# Local projection
# ---------------------------------------------------------------------------

def _make_local_transformers(center):
    """
    Construct forward and reverse transformations for a local AEQD CRS.

    Input and output coordinates are WGS84 latitude/longitude.
    Local coordinates are meters (x=east, y=north).
    """

    lat, lon = center

    local_crs = CRS.from_proj4(
        f"+proj=aeqd "
        f"+lat_0={lat} "
        f"+lon_0={lon} "
        f"+datum=WGS84 "
        f"+units=m "
        f"+no_defs"
    )

    forward = Transformer.from_crs(
        "EPSG:4326",
        local_crs,
        always_xy=True,
    )

    reverse = Transformer.from_crs(
        local_crs,
        "EPSG:4326",
        always_xy=True,
    )

    return forward, reverse


def _project_point(transformer, coordinate):
    """Convert (latitude, longitude) to local (x, y)."""

    lat, lon = coordinate

    x, y = transformer.transform(lon, lat)

    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Coordinate projection produced invalid values.")

    return x, y


def _unproject_point(transformer, point):
    """Convert local (x, y) to WGS84 (latitude, longitude)."""

    lon, lat = transformer.transform(point[0], point[1])

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError("Reverse projection produced invalid coordinates.")

    # Normalize longitude to the conventional WGS84 range.
    lon = ((lon + 180) % 360) - 180

    return lat, lon


# ---------------------------------------------------------------------------
# Rectangle geometry
# ---------------------------------------------------------------------------

def _bearing_vectors(bearing):
    """
    **bearing** : *float, optional*
        Clockwise rotation of the boundary from a north-oriented
        square or rectangle.

        A bearing of 0 produces a north-oriented boundary.
        A bearing of 45 rotates the boundary 45 degrees clockwise.

        Default: 0 degrees.
    """
    theta = math.radians(90 + bearing)

    # Direction along the top edge (TL -> TR).
    u = (math.sin(theta), math.cos(theta))

    # Direction along the right/down edge (TR -> BR).
    v = (math.cos(theta), -math.sin(theta))

    return u, v


def _add_vectors(origin, vector, distance):
    """Move a point along a unit vector by a given distance."""

    return (
        origin[0] + vector[0] * distance,
        origin[1] + vector[1] * distance,
    )


def _calculate_rectangle(top_left, width, height, bearing):
    """Calculate four rectangle corners in local coordinates."""

    u, v = _bearing_vectors(bearing)

    top_right = _add_vectors(top_left, u, width)

    bottom_left = _add_vectors(top_left, v, height)

    bottom_right = _add_vectors(bottom_left, u, width)

    return [
        top_left,
        top_right,
        bottom_right,
        bottom_left,
    ]


def _generate_ratio_rectangle(
    top_left,
    top_right,
    aspect_ratio,
):
    """
    Generate a rectangle from its top edge and width-to-height ratio.

    The supplied top-left and top-right coordinates define the top edge.
    The aspect ratio determines the height.

    The bottom edge is constructed perpendicular to the top edge,
    extending downwards in map-grid order.

    The projection centre is iteratively adjusted to match the
    geodesic midpoint of the TL-BR diagonal.
    """

    geod = Geod(ellps="WGS84")

    ratio = _validate_aspect_ratio(aspect_ratio)

    # Begin with the geodesic midpoint of the supplied top edge.
    projection_center = _geodesic_midpoint(
        top_left,
        top_right,
    )

    def construct_corners(center):
        forward, reverse = _make_local_transformers(center)

        tl = _project_point(forward, top_left)
        tr = _project_point(forward, top_right)

        dx = tr[0] - tl[0]
        dy = tr[1] - tl[1]

        width = math.hypot(dx, dy)

        if width <= 0:
            raise ValueError(
                "top_left and top_right must be distinct points."
            )

        # Unit vector along the top edge.
        u = (dx / width, dy / width)

        # Perpendicular unit vector pointing down the map.
        v = (u[1], -u[0])

        height = width / ratio

        bl = _add_vectors(tl, v, height)
        br = _add_vectors(tr, v, height)

        local_corners = [
            tl,
            tr,
            br,
            bl,
        ]

        geographic_corners = [
            _unproject_point(reverse, point)
            for point in local_corners
        ]

        return geographic_corners

    # Iteratively align the projection centre with the TL-BR
    # geodesic midpoint.
    for _ in range(30):
        corners = construct_corners(projection_center)

        new_center = _geodesic_midpoint(
            corners[0],
            corners[2],
        )

        _, _, shift = geod.inv(
            projection_center[1],
            projection_center[0],
            new_center[1],
            new_center[0],
        )

        projection_center = new_center

        if shift < 0.001:
            break

    # Reconstruct using the final projection centre.
    return construct_corners(projection_center)

# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

def _export_shapefiles(
    corners,
    center,
    point_shapefile=None,
    polygon_shapefile=None,
    output_crs="EPSG:4326",
):
    """Export boundary points and polygon to shapefiles."""

    if point_shapefile is None and polygon_shapefile is None:
        return

    try:
        output_crs = CRS.from_user_input(output_crs)
    except CRSError as exc:
        raise ValueError(
            f"Invalid output CRS: {output_crs}"
        ) from exc

    if point_shapefile is not None:
        point_data = []

        names = ["TL", "TR", "BR", "BL"]

        for index, (name, coordinate) in enumerate(
            zip(names, corners),
            start=1,
        ):
            lat, lon = coordinate

            point_data.append({
                "point_id": index,
                "role": name,
                "latitude": lat,
                "longitude": lon,
                "geometry": Point(lon, lat),
            })

        # Include the center as an additional point.
        lat, lon = center

        point_data.append({
            "point_id": 5,
            "role": "CENTER",
            "latitude": lat,
            "longitude": lon,
            "geometry": Point(lon, lat),
        })

        points = gpd.GeoDataFrame(
            point_data,
            geometry="geometry",
            crs="EPSG:4326",
        )

        points = points.to_crs(output_crs)

        Path(point_shapefile).parent.mkdir(parents=True, exist_ok=True)
        points.to_file(
            point_shapefile,
            driver="ESRI Shapefile",
            index=False,
        )

    if polygon_shapefile is not None:
        # Shapely expects longitude, latitude coordinates.
        polygon = Polygon([
            (lon, lat)
            for lat, lon in corners
        ])

        if not polygon.is_valid:
            raise ValueError(
                "Generated polygon is invalid and cannot be exported."
            )

        polygons = gpd.GeoDataFrame(
            [{"bound_id": 1}],
            geometry=[polygon],
            crs="EPSG:4326",
        )

        polygons = polygons.to_crs(output_crs)

        Path(polygon_shapefile).parent.mkdir(parents=True, exist_ok=True)
        polygons.to_file(
            polygon_shapefile,
            driver="ESRI Shapefile",
            index=False,
        )


def _geodesic_midpoint(point_a, point_b):
    """
    Return the geodesic midpoint between two (lat, lon) points.
    """
    geod = Geod(ellps="WGS84")

    lat1, lon1 = point_a
    lat2, lon2 = point_b

    azimuth, _, distance = geod.inv(
        lon1, lat1,
        lon2, lat2,
    )

    lon_mid, lat_mid, _ = geod.fwd(
        lon1, lat1,
        azimuth,
        distance / 2,
    )

    return lat_mid, lon_mid


def _make_aeqd_crs(center):
    """
    Create a local Azimuthal Equidistant CRS centred on a (lat, lon).
    """
    lat0, lon0 = center

    return CRS.from_proj4(
        f"+proj=aeqd "
        f"+lat_0={lat0} "
        f"+lon_0={lon0} "
        f"+datum=WGS84 "
        f"+units=m "
        f"+no_defs"
    )



def _generate_square_from_top_left(top_left, side_length_m, bearing):
    """
    Generate square corners from a top-left coordinate and side length.

    The AEQD projection centre is iteratively adjusted until it
    coincides with the geodesic midpoint of the TL-BR diagonal.
    This makes the generated square compatible with bother()'s
    rectangle validation.
    """
    lat_tl, lon_tl = top_left
    center = (lat_tl, lon_tl)

    geod = Geod(ellps="WGS84")
    u, v = _bearing_vectors(bearing)

    for _ in range(30):
        local_crs = _make_aeqd_crs(center)

        forward = Transformer.from_crs(
            CRS.from_epsg(4326),
            local_crs,
            always_xy=True,
        )
        inverse = Transformer.from_crs(
            local_crs,
            CRS.from_epsg(4326),
            always_xy=True,
        )

        # Project the fixed top-left coordinate into the current CRS.
        x_tl, y_tl = forward.transform(lon_tl, lat_tl)

        # Construct the other three corners in the local projection.
        x_tr = x_tl + side_length_m * u[0]
        y_tr = y_tl + side_length_m * u[1]

        x_br = x_tr + side_length_m * v[0]
        y_br = y_tr + side_length_m * v[1]

        x_bl = x_tl + side_length_m * v[0]
        y_bl = y_tl + side_length_m * v[1]

        projected_corners = [
            (x_tl, y_tl),
            (x_tr, y_tr),
            (x_br, y_br),
            (x_bl, y_bl),
        ]

        corners = []
        for x, y in projected_corners:
            lon, lat = inverse.transform(x, y)
            corners.append((lat, lon))

        # The canonical projection centre is the geodesic midpoint
        # of the resulting TL-BR diagonal.
        new_center = _geodesic_midpoint(corners[0], corners[2])

        _, _, center_shift = geod.inv(
            center[1], center[0],
            new_center[1], new_center[0],
        )

        center = new_center

        # Stop once the projection centre has converged to within 1 mm.
        if center_shift < 0.001:
            break

    # Rebuild the corners using the final projection centre.
    local_crs = _make_aeqd_crs(center)

    forward = Transformer.from_crs(
        CRS.from_epsg(4326),
        local_crs,
        always_xy=True,
    )
    inverse = Transformer.from_crs(
        local_crs,
        CRS.from_epsg(4326),
        always_xy=True,
    )

    x_tl, y_tl = forward.transform(lon_tl, lat_tl)

    projected_corners = [
        (x_tl, y_tl),
        (
            x_tl + side_length_m * u[0],
            y_tl + side_length_m * u[1],
        ),
        (
            x_tl + side_length_m * (u[0] + v[0]),
            y_tl + side_length_m * (u[1] + v[1]),
        ),
        (
            x_tl + side_length_m * v[0],
            y_tl + side_length_m * v[1],
        ),
    ]

    corners = []
    for x, y in projected_corners:
        lon, lat = inverse.transform(x, y)
        corners.append((lat, lon))

    return corners


def _generate_square_from_center(center_point, radius_m, bearing):
    """
    Generate square corners from a center point and circumradius.

    The supplied center remains the geometric center of the square.
    The AEQD projection centre is iteratively aligned with the
    geodesic midpoint of the TL-BR diagonal.
    """

    geod = Geod(ellps="WGS84")

    side = radius_m * math.sqrt(2)
    half_side = side / 2

    u, v = _bearing_vectors(bearing)

    projection_center = center_point

    def construct_corners(center):
        forward, reverse = _make_local_transformers(center)

        local_center = _project_point(forward, center_point)

        local_top_left = (
            local_center[0] - half_side * u[0] - half_side * v[0],
            local_center[1] - half_side * u[1] - half_side * v[1],
        )

        local_corners = _calculate_rectangle(
            local_top_left,
            side,
            side,
            bearing,
        )

        return [
            _unproject_point(reverse, point)
            for point in local_corners
        ]

    for _ in range(30):
        corners = construct_corners(projection_center)

        new_center = _geodesic_midpoint(
            corners[0],
            corners[2],
        )

        _, _, shift = geod.inv(
            projection_center[1],
            projection_center[0],
            new_center[1],
            new_center[0],
        )

        projection_center = new_center

        if shift < 0.001:
            break

    return construct_corners(projection_center)

# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def generate_boundary(
    top_left=None,
    top_right=None,
    bottom_right=None,
    side_length=None,
    center=None,
    radius=None,
    aspect_ratio=None,
    bearing=0,
    unit="km",
    point_shapefile=None,
    polygon_shapefile=None,
    output_crs="EPSG:4326",
):
    """
    Generate a valid square or rectangular geographic boundary.

    Parameters
    ----------
    **top_left** : *tuple, optional*
        Top-left corner as (latitude, longitude).

        Used for:
            - Square defined by top-left and side_length.
            - Rectangle defined by top_left and bottom_right.

    **top_right** : *tuple, optional*
        Top-right corner as (latitude, longitude).

        Used with top_left and aspect_ratio to generate a rectangle.

    **bottom_right** : *tuple, optional*
        Bottom-right corner as (latitude, longitude).

        Used only when generating a rectangle.

    **side_length** : *float, optional*
        Square side length.

        Used with top_left.

    **center** : *tuple, optional*
        Square center as (latitude, longitude).

        Used with radius.

    **radius** : *float, optional*
        Square circumradius: distance from center to any corner.

        Used with center.

    **aspect_ratio** : *tuple, optional*
        Rectangle width-to-height ratio, expressed as (width, height).

        Examples:
            (2, 1)
            (1, 4)
            (1, 64)

        Used with top_left and top_right.

    **bearing** : *float, optional*
        Clockwise rotation from a north-oriented boundary, in degrees.
    
        Used when generating a square from top_left + side_length,
        center + radius, or a rectangle from top_left + bottom_right.
    
        When using top_left + top_right + aspect_ratio, the supplied
        top edge determines the orientation and bearing is ignored.
    
        Default: 0 degrees.

    **unit** : *str, optional*
        Distance unit for side_length or radius.

        Supported: meters, kilometers, centimeters, millimeters,
        feet, yards, miles, nautical miles.

        Default: kilometers.

    **point_shapefile** : *str, optional*
        Output path for a point shapefile containing the four corners
        and the center point.

    **polygon_shapefile** : *str, optional*
        Output path for a polygon shapefile containing the boundary.

    **output_crs** : *str, int, optional*
        CRS used for shapefile exports.

        Default: EPSG:4326.

        Returned corner coordinates always remain WGS84.

    Returns
    -------
    list
        Four (latitude, longitude) coordinate pairs in the order:

            1. Top-left
            2. Top-right
            3. Bottom-right
            4. Bottom-left

        The returned list can be passed directly to:

            otter.bother(corners=corners, ...)

    Notes
    -----
    Calculations use a local Azimuthal Equidistant projection.

    The generated rectangle has straight, perpendicular edges in this
    local projected coordinate system. For extremely large boundaries,
    projection distortion increases.
    """

    bearing = _normalize_bearing(bearing)

    # Determine which generation method is being requested.
    square_from_corner = (
        top_left is not None
        and side_length is not None
        and top_right is None
        and bottom_right is None
        and center is None
        and radius is None
        and aspect_ratio is None
    )

    square_from_center = (
        center is not None
        and radius is not None
        and top_left is None
        and top_right is None
        and bottom_right is None
        and side_length is None
        and aspect_ratio is None
    )

    rectangle_from_corners = (
        top_left is not None
        and bottom_right is not None
        and top_right is None
        and side_length is None
        and center is None
        and radius is None
        and aspect_ratio is None
    )

    rectangle_from_top_edge = (
        top_left is not None
        and top_right is not None
        and aspect_ratio is not None
        and bottom_right is None
        and side_length is None
        and center is None
        and radius is None
    )

    methods = [
        square_from_corner,
        square_from_center,
        rectangle_from_corners,
        rectangle_from_top_edge,
    ]

    if sum(methods) != 1:
        raise ValueError(
            "Invalid boundary arguments. Supply exactly one of:\n"
            "1. top_left + side_length\n"
            "2. center + radius\n"
            "3. top_left + bottom_right\n"
            "4. top_left + top_right + aspect_ratio"
        )


    # ---------------------------------------------------------------
    # Square: top-left corner + side length
    # ---------------------------------------------------------------

    if square_from_corner:
        top_left = _validate_coordinate(top_left, "top_left")

        side = _to_meters(side_length, unit)

        corners = _generate_square_from_top_left(
            top_left=top_left,
            side_length_m=side,
            bearing=bearing,
        )


    # ---------------------------------------------------------------
    # Square: center + circumradius
    # ---------------------------------------------------------------

    elif square_from_center:
        center = _validate_coordinate(center, "center")

        radius_m = _to_meters(radius, unit)

        corners = _generate_square_from_center(
            center_point=center,
            radius_m=radius_m,
            bearing=bearing,
        )


    # ---------------------------------------------------------------
    # Rectangle: top-left + bottom-right + bearing
    # ---------------------------------------------------------------

    elif rectangle_from_corners:

        top_left = _validate_coordinate(top_left, "top_left")
        bottom_right = _validate_coordinate(
            bottom_right,
            "bottom_right",
        )


        projection_center = _geodesic_midpoint(
            top_left,
            bottom_right,
        )

        forward, reverse = _make_local_transformers(
            projection_center
        )

        local_top_left = _project_point(forward, top_left)

        local_bottom_right = _project_point(
            forward,
            bottom_right,
        )

        dx = local_bottom_right[0] - local_top_left[0]
        dy = local_bottom_right[1] - local_top_left[1]

        u, v = _bearing_vectors(bearing)

        # Resolve the diagonal into the rectangle's two perpendicular axes.
        width = dx * u[0] + dy * u[1]
        height = dx * v[0] + dy * v[1]

        if width <= 0 or height <= 0:
            raise ValueError(
                "The supplied top_left, bottom_right, and bearing "
                "do not define a valid rectangle. Check the corner "
                "coordinates and bearing."
            )


        inferred_ratio = width / height
        ratio_exponent = math.log2(inferred_ratio)
        
        if (
            not math.isclose(
                ratio_exponent,
                round(ratio_exponent),
                rel_tol=0,
                abs_tol=1e-9,
            )
            or not -8 <= ratio_exponent <= 8
        ):
            warnings.warn(
                "The inferred geographic boundary has an aspect ratio "
                "that is not compatible with an OpenTTD map. The resulting "
                "heightmap may be distorted when fitted to the requested "
                "map dimensions. Consider using top_left, top_right, and "
                "aspect_ratio to specify an OpenTTD-compatible ratio.",
                UserWarning,
                stacklevel=2,
            )
        else:
            warnings.warn(
                "Generating a rectangle from top_left and bottom_right "
                "infers its aspect ratio. Consider using top_left, "
                "top_right, and aspect_ratio if you want to specify "
                "the dimensions explicitly.",
                UserWarning,
                stacklevel=2,
            )
        
        
        local_corners = _calculate_rectangle(
            local_top_left,
            width,
            height,
            bearing,
        )

        # Verify the generated BR agrees with the supplied BR.
        generated_br = local_corners[2]

        closure_error = math.hypot(
            generated_br[0] - local_bottom_right[0],
            generated_br[1] - local_bottom_right[1],
        )
        
        
        geod = Geod(ellps="WGS84")

        _, _, distance = geod.inv(
            top_left[1],
            top_left[0],
            bottom_right[1],
            bottom_right[0],
        )

        if not math.isfinite(distance) or distance <= 0:
            raise ValueError(
                "Top-left and bottom-right must be distinct points."
            )

        if closure_error > max(0.01, distance * 1e-7):
            raise ValueError(
                "The supplied coordinates and bearing do not produce "
                "a sufficiently consistent rectangle."
            )

        corners = [
            _unproject_point(reverse, point)
            for point in local_corners
        ]

    # ---------------------------------------------------------------
    # Rectangle: top-left + top-right + aspect ratio
    # ---------------------------------------------------------------

    elif rectangle_from_top_edge:
        _validate_coordinate(top_left, "top_left")
        _validate_coordinate(top_right, "top_right")
    
        _validate_aspect_ratio(aspect_ratio)
    
        corners = _generate_ratio_rectangle(
            top_left,
            top_right,
            aspect_ratio,
        )


    # ---------------------------------------------------------------
    # Calculate the geographic center of the generated boundary.
    # ---------------------------------------------------------------

    # Use the same canonical center as bother() validation:
    # the geodesic midpoint of the TL-BR diagonal.
    generated_center = _geodesic_midpoint(
        corners[0],
        corners[2],
    )

    # ---------------------------------------------------------------
    # Optional shapefile exports.
    # ---------------------------------------------------------------

    _export_shapefiles(
        corners=corners,
        center=generated_center,
        point_shapefile=point_shapefile,
        polygon_shapefile=polygon_shapefile,
        output_crs=output_crs,
    )

    return corners
