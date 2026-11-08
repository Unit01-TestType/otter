'''
This script contains an adaptation of bother by bunburya for to work with otter to retrieve terrain data
and create a png and tif raster for the heightmap.

NOTE: TRANSFORMATION USE WEB MERCATOR WHEN DEALING WITH ROTATED BOUDNARIES WHICH CAN ONLY BE
APPROXIMATELY TRANSFORMED BACK TO WGS84

This was heavily modified using AI to add support for rotated boundaries.

bother: https://github.com/bunburya/bother/tree/master


API format:
    
otter.bother(
    corners=[
        (lat_top_left, lon_top_left),
        (lat_top_right, lon_top_right),
        (lat_bottom_right, lon_bottom_right),
        (lat_bottom_left, lon_bottom_left),
    ],
    outfile=...,
    outfile_tif=...,
    scale_image='2048x4096',
    ...
)


Corner order is map-grid order which may not necessarily be compass order. For example,
"top" means the top of the game map, not necessarily geogrpahic north

TODO:
    - check CRS of geodataframes and shapefile and reproject to 4326 rather than force 4326 input

'''


import sys
import math
import time
import os
import os.path
import tempfile
import warnings
from typing import Optional, Set, Tuple, List

from PIL import Image
from rasterio.io import MemoryFile

from pyproj import CRS, Geod, Transformer
from pyproj.exceptions import CRSError

from affine import Affine

from otter.bother_utils.srtm import create_tif_file, clear_cache
from otter.bother_utils.heightmap import (
    remove_sea,
    resample,
    reproject_raster,
    set_lakes_to_elev,
    raise_undersea_land,
    raise_low_pixels,
    to_png,
    crop_modes,
    crop_image,
    scale_image_f,
    png_to_file,
)

import geopandas as gpd
import pandas as pd
import numpy as np

from scipy.ndimage import map_coordinates

# EPSG codes
WGS84 = 4326  # Mercator - The default CRS used in the STRM data
PSEUDO_MERCATOR = 3857  # Web Mercator - The projection used by Google Maps, OpenStreetMap, etc.

def error(msg: str):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# ROTATION:
# New helpers for converting the old bounds representation into the new
# four-corner representation and validating oriented quadrilaterals.
# ---------------------------------------------------------------------------

def _bounds_to_corners(bounds):
    """
    Convert the legacy bounds format:

        [lat_bottom, lon_left, lat_top, lon_right]

    into map-grid ordered corners:

        [
            (lat_top_left, lat_top_right),
            (lat_top_right, lon_right),
            (lat_bottom_right, lon_right),
            (lat_bottom_left, lon_left),
        ]

    More precisely, the returned tuples are (lat, lon), and the order is:

        top-left, top-right, bottom-right, bottom-left
    """
    lat_bottom, lon_left, lat_top, lon_right = bounds

    return [
        (lat_top, lon_left),
        (lat_top, lon_right),
        (lat_bottom, lon_right),
        (lat_bottom, lon_left),
    ]


def _normalize_corners(corners):
    """
    Validate basic structure of the new corners argument.

    corners are expected as four (lat, lon) pairs in this order:

        top-left
        top-right
        bottom-right
        bottom-left
    """
    if not isinstance(corners, (list, tuple)) or len(corners) != 4:
        raise ValueError(
            'corners must contain exactly 4 coordinate pairs in the order '
            'top-left, top-right, bottom-right, bottom-left.'
        )

    normalized = []

    for i, corner in enumerate(corners):
        if not isinstance(corner, (list, tuple)) or len(corner) != 2:
            raise ValueError(
                f'Corner {i} must be a (latitude, longitude) pair.'
            )

        try:
            lat = float(corner[0])
            lon = float(corner[1])
        except (TypeError, ValueError):
            raise ValueError(
                f'Corner {i} contains invalid latitude/longitude values.'
            )

        if not -90 <= lat <= 90:
            raise ValueError(f'Corner {i} has invalid latitude: {lat}.')

        if not -180 <= lon <= 180:
            raise ValueError(f'Corner {i} has invalid longitude: {lon}.')

        normalized.append((lat, lon))

    return normalized



def _project_corners_for_validation(corners):
    """
    Project corners into a local Azimuthal Equidistant (AEQD) CRS
    for geometric validation.

    The projection is centred on the geodesic midpoint of the
    top-left and bottom-right corners. This is the canonical
    projection centre used by generate_boundary().
    """
    geod = Geod(ellps="WGS84")

    lat1, lon1 = corners[0]
    lat2, lon2 = corners[2]

    azimuth, _, distance = geod.inv(
        lon1, lat1,
        lon2, lat2,
    )

    lon0, lat0, _ = geod.fwd(
        lon1, lat1,
        azimuth,
        distance / 2,
    )

    local_crs = CRS.from_proj4(
        f"+proj=aeqd "
        f"+lat_0={lat0} "
        f"+lon_0={lon0} "
        f"+datum=WGS84 "
        f"+units=m "
        f"+no_defs"
    )

    transformer = Transformer.from_crs(
        CRS.from_epsg(4326),
        local_crs,
        always_xy=True,
    )

    return [
        transformer.transform(lon, lat)
        for lat, lon in corners
    ]



def _vector(a, b):
    return (b[0] - a[0], b[1] - a[1])


def _length(v):
    return math.hypot(v[0], v[1])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _vectors_parallel(a, b, tolerance=1e-6):
    """
    Test whether two vectors are parallel using a normalized cross product.
    """
    denominator = _length(a) * _length(b)

    if denominator == 0:
        return False

    return abs(_cross(a, b)) / denominator <= tolerance


def _vectors_perpendicular(a, b, tolerance=1e-6):
    denominator = _length(a) * _length(b)

    if denominator == 0:
        return False

    return abs(_dot(a, b)) / denominator <= tolerance


def _validate_corners(corners):
    """
    Validate four geographic corners defining a convex quadrilateral.

    Corners are in map-grid order:

        top-left
        top-right
        bottom-right
        bottom-left

    Opposite sides do not need to be parallel, and adjacent sides
    do not need to be perpendicular.
    """
    corners = _normalize_corners(corners)

    projected = _project_corners_for_validation(corners)

    # Check that all corners are distinct.
    for i in range(4):
        for j in range(i + 1, 4):
            if _length(_vector(projected[i], projected[j])) < 0.01:
                raise ValueError(
                    'corners must contain four distinct points.'
                )

    # Check that the quadrilateral is convex and consistently ordered.
    cross_products = []

    for i in range(4):
        p1 = projected[i]
        p2 = projected[(i + 1) % 4]
        p3 = projected[(i + 2) % 4]

        edge1 = _vector(p1, p2)
        edge2 = _vector(p2, p3)

        cross_products.append(_cross(edge1, edge2))

    if any(abs(value) < 1e-6 for value in cross_products):
        raise ValueError(
            'corners define a degenerate quadrilateral with '
            'collinear consecutive points.'
        )

    signs = [value > 0 for value in cross_products]

    if not all(sign == signs[0] for sign in signs):
        raise ValueError(
            'corners must define a convex quadrilateral in the order '
            'top-left, top-right, bottom-right, bottom-left. '
            'The supplied boundary may be self-intersecting or concave.'
        )

    # Check that the polygon has a meaningful area.
    area = 0.5 * abs(sum(
        projected[i][0] * projected[(i + 1) % 4][1]
        - projected[(i + 1) % 4][0] * projected[i][1]
        for i in range(4)
    ))

    if area < 1.0:
        raise ValueError(
            'The supplied corners define a boundary that is too small '
            'or degenerate to process.'
        )

    return corners


def _corners_to_enclosing_bounds(corners):
    """
    Return the ordinary axis-aligned WGS84 bounding box required to retrieve
    enough source SRTM data.

    This does NOT define the output raster orientation. It is only the
    source-data acquisition envelope.
    """
    lats = [corner[0] for corner in corners]
    lons = [corner[1] for corner in corners]

    return (
        min(lons),
        min(lats),
        max(lons),
        max(lats),
    )


def _make_destination_transform(corners, width, height, dst_crs):
    """
    Construct the affine transform for the destination game-grid.

    corners are WGS84 (lat, lon) coordinates in map-grid order:

        top-left
        top-right
        bottom-right
        bottom-left

    The transform is created in the requested destination CRS.
    """
    transformer = Transformer.from_crs(
        'EPSG:4326',
        dst_crs,
        always_xy=True,
    )

    a = transformer.transform(corners[0][1], corners[0][0])
    b = transformer.transform(corners[1][1], corners[1][0])
    d = transformer.transform(corners[3][1], corners[3][0])

    # Affine transform convention:
    #
    # x = a + col * pixel_x + row * pixel_y_x
    # y = b + col * pixel_y + row * pixel_y_y
    #
    # Use pixel-edge coordinates below. The half-pixel offset is applied so
    # that the supplied corners represent the outer corners of the raster.
    from affine import Affine

    pixel_col_x = (b[0] - a[0]) / width
    pixel_col_y = (b[1] - a[1]) / width

    pixel_row_x = (d[0] - a[0]) / height
    pixel_row_y = (d[1] - a[1]) / height

    origin_x = a[0] + 0.5 * pixel_col_x + 0.5 * pixel_row_x
    origin_y = a[1] + 0.5 * pixel_col_y + 0.5 * pixel_row_y

    return Affine(
        pixel_col_x,
        pixel_row_x,
        origin_x,
        pixel_col_y,
        pixel_row_y,
        origin_y,
    )



def _warp_quadrilateral_raster(
    memfile,
    corners,
    width,
    height,
    dst_crs,
):
    """
    Warp an elevation raster to a four-corner destination grid.

    The interior of the requested boundary is defined in Web Mercator
    (EPSG:3857), using bilinear interpolation between the four supplied
    corners.

    Corner order:
        top-left, top-right, bottom-right, bottom-left

    Output positions are sampled at pixel centers. Source raster
    coordinates are converted from pixel-edge coordinates to
    pixel-center array indices before interpolation.
    """

    # ---------------------------------------------------------------
    # Validate and prepare coordinates.
    # ---------------------------------------------------------------

    if width <= 0 or height <= 0:
        raise ValueError("Output raster dimensions must be positive.")

    if len(corners) != 4:
        raise ValueError("Exactly four corners are required.")

    # Input coordinates are (latitude, longitude).
    latitudes = np.asarray(
        [point[0] for point in corners],
        dtype=np.float64,
    )

    longitudes = np.asarray(
        [point[1] for point in corners],
        dtype=np.float64,
    )

    # Web Mercator is undefined at the poles.
    max_mercator_lat = 85.0511287798066

    if np.any(np.abs(latitudes) > max_mercator_lat):
        raise ValueError(
            "Corner latitudes must be between "
            "-85.05112878 and 85.05112878 degrees "
            "for Web Mercator transformation."
        )

    # ---------------------------------------------------------------
    # Project the four corners into Web Mercator.
    # ---------------------------------------------------------------

    wgs84_to_mercator = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:3857",
        always_xy=True,
    )

    corner_x, corner_y = wgs84_to_mercator.transform(
        longitudes,
        latitudes,
    )

    tl_x, tr_x, br_x, bl_x = corner_x
    tl_y, tr_y, br_y, bl_y = corner_y

    # ---------------------------------------------------------------
    # Generate output pixel-center coordinates.
    #
    # Each pixel center is represented by normalized coordinates
    # between 0 and 1 across the requested quadrilateral.
    # ---------------------------------------------------------------

    u = (
        np.arange(width, dtype=np.float64) + 0.5
    ) / width

    v = (
        np.arange(height, dtype=np.float64) + 0.5
    ) / height

    uu, vv = np.meshgrid(u, v)

    # ---------------------------------------------------------------
    # Bilinear interpolation across all four corners.
    #
    # For a parallelogram, this reduces to an affine transformation.
    # For a general convex quadrilateral, it preserves all four
    # supplied corner positions.
    # ---------------------------------------------------------------

    mercator_x = (
        (1 - uu) * (1 - vv) * tl_x
        + uu * (1 - vv) * tr_x
        + uu * vv * br_x
        + (1 - uu) * vv * bl_x
    )

    mercator_y = (
        (1 - uu) * (1 - vv) * tl_y
        + uu * (1 - vv) * tr_y
        + uu * vv * br_y
        + (1 - uu) * vv * bl_y
    )

    # ---------------------------------------------------------------
    # Transform destination positions into the source raster CRS.
    # ---------------------------------------------------------------

    with memfile.open() as src:

        if src.crs is None:
            raise ValueError(
                "Source elevation raster has no defined CRS."
            )

        source_data = src.read(1).astype(np.float32)

        source_transform = src.transform
        source_crs = src.crs
        source_nodata = src.nodata

        mercator_to_source = Transformer.from_crs(
            "EPSG:3857",
            source_crs,
            always_xy=True,
        )

        source_x, source_y = mercator_to_source.transform(
            mercator_x,
            mercator_y,
        )

        # -----------------------------------------------------------
        # Convert map coordinates into source raster coordinates.
        #
        # The inverse affine transform returns coordinates measured
        # from the upper-left pixel corner. SciPy array indices refer
        # to pixel centers, so subtract 0.5 from each coordinate.
        # -----------------------------------------------------------

        inverse_transform = ~source_transform

        source_cols, source_rows = inverse_transform * (
            source_x,
            source_y,
        )

        source_cols = source_cols - 0.5
        source_rows = source_rows - 0.5

        # -----------------------------------------------------------
        # Bilinear elevation sampling.
        # -----------------------------------------------------------

        if source_nodata is None:
            cval = np.nan
        else:
            cval = float(source_nodata)

        warped_data = map_coordinates(
            source_data,
            [
                source_rows.ravel(),
                source_cols.ravel(),
            ],
            order=1,
            mode="constant",
            cval=cval,
            prefilter=False,
        ).reshape((height, width))

        # -----------------------------------------------------------
        # Construct destination raster georeferencing.
        #
        # An affine transform can represent the exact grid when the
        # destination corners form a parallelogram in dst_crs.
        # For a general quadrilateral, it is an approximation; the
        # sampled elevation values above still use all four corners.
        # -----------------------------------------------------------

        wgs84_to_destination = Transformer.from_crs(
            "EPSG:4326",
            dst_crs,
            always_xy=True,
        )

        dst_x, dst_y = wgs84_to_destination.transform(
            longitudes,
            latitudes,
        )

        dst_tl_x, dst_tr_x, _, dst_bl_x = dst_x
        dst_tl_y, dst_tr_y, _, dst_bl_y = dst_y

        destination_transform = Affine(
            (dst_tr_x - dst_tl_x) / width,
            (dst_bl_x - dst_tl_x) / height,
            dst_tl_x,
            (dst_tr_y - dst_tl_y) / width,
            (dst_bl_y - dst_tl_y) / height,
            dst_tl_y,
        )

        # -----------------------------------------------------------
        # Write the warped raster into a new in-memory GeoTIFF.
        # -----------------------------------------------------------

        profile = src.profile.copy()

        profile.update(
            driver="GTiff",
            width=width,
            height=height,
            count=1,
            dtype="float32",
            crs=dst_crs,
            transform=destination_transform,
            nodata=source_nodata,
        )

    output_memfile = MemoryFile()

    with output_memfile.open(**profile) as dst:
        dst.write(warped_data.astype(np.float32), 1)

    return output_memfile



def bother(
    outfile,
    bounds=None,
    corners=None,
    outfile_tif=None,
    infile_tif=None,
    scale_data=None,
    epsg='4326',
    raise_low=0,
    raise_undersea=None,
    no_sea=None,
    lakes=None,
    max_brightness=255,
    infile_png=None,
    crop=None,
    scale_image=None,
):
    '''
    Run bother to download SRTM elevation data.

    Parameters
    ----------
    **outfile** : *str, path*
        The file to which the greyscale PNG image will be written.

    **bounds** : *list, GeoDataFrame, str, path*, optional
        Legacy axis-aligned bounding box.

        List format:
            [latitude_bottom, longitude_left,
             latitude_top, longitude_right]

        DEPRECATED: use corners instead.

        bounds must describe a north-oriented bounding box. Rotated or
        otherwise non-axis-aligned input is not supported reliably and may
        produce unintended results.

    **corners** : *list*, optional
        Four WGS84 coordinate pairs in (latitude, longitude) order:
    
            [
                (top_left),
                (top_right),
                (bottom_right),
                (bottom_left)
            ]
    
        The four points must define a valid convex quadrilateral.
        They do not need to form a perfect rectangle.
    
        When scale_image is supplied, the elevation raster is warped
        to fit the requested output dimensions using all four corners.
        The geographic aspect ratio does not need to match the
        output raster aspect ratio.


    **outfile_tif** : *str, path*
        Path to output tif file.

    **infile_tif** : *str, path, optional*
        Path to a tif file containing elevation data.

    **scale_data** : *float, optional*
        More than 1 will upsample the data resolution; less than 1 downsample.

    **epsg** : *int, optional*
        Coordinate Reference System EPSG code to project data.

    **raise_low** : *float, optional*
        Values below the input will be rounded down to 0.

    **raise_undersea** : *int, optional*
        Raise pixels with elevation below zero.

    **no_sea** : *float, optional*
        Raise pixels with low elevation.

    **lakes** : *int, optional*
        Detect lakes and set to 0.

    **max_brightness** : *int, optional*
        Maximum heightmap brightness.

    **infile_png** : *str, path, optional*
        Existing PNG input.

    **crop** : *str, optional*
        Crop resulting image.

    **scale_image** : *str, optional*
        Scale resulting image to WIDTHxHEIGHT.

    Returns
    -------
    Writes GeoTIFF and/or PNG.
    '''
    
    
    '''
    Check inputs - adapted from check_namespace
    '''
    
    # -----------------------------------------------------------------------
    # Input validation
    # -----------------------------------------------------------------------

    if (
        bounds is None
        and corners is None
        and infile_tif is None
        and infile_png is None
    ):
        error('Must pass corners, bounds, infile_tif or infile_png.')

    if sum(
        value is not None
        for value in (bounds, corners, infile_tif, infile_png)
    ) > 1:
        error(
            'corners, bounds, infile_tif and infile_png are mutually exclusive.'
        )
    
    
    # -----------------------------------------------------------------------
    # Parse target image dimensions early.
    #
    # ROTATION:
    # The destination raster must be created at the final game-grid
    # dimensions rather than being resized after georeferencing.
    # -----------------------------------------------------------------------
    
    map_width = None
    map_height = None

    if scale_image:
        res = scale_image.split('x')

        try:
            map_width = int(res[0])
            map_height = int(res[1])
        except (IndexError, ValueError):
            error(
                'Size for scaled image must be in form '
                '"WIDTHxHEIGHT", where WIDTH and HEIGHT are integers.'
            )

        if map_width <= 0 or map_height <= 0:
            error(
                f'Invalid dimensions for scaling: '
                f'{map_width}x{map_height}.'
            )

    # Crop remains an image operation. It is not part of the rotated
    # destination-grid definition.
    if crop:
        res, mode = crop

        if mode.lower() not in crop_modes:
            error(f'Mode must be one of {crop_modes}.')

        res = res.split('x')

        try:
            width = int(res[0])
            height = int(res[1])
        except (IndexError, ValueError):
            error(
                'Size for cropped image must be in form '
                '"WIDTHxHEIGHT", where WIDTH and HEIGHT are integers.'
            )

        if width <= 0 or height <= 0:
            error(f'Invalid dimensions for cropping: {width}x{height}.')
            
    
    # -----------------------------------------------------------------------
    # Normalize bounds/corners.
    # -----------------------------------------------------------------------

    normalized_corners = None
    
    # Track whether the user explicitly supplied four corners.
    # Legacy bounds may also be converted into normalized_corners,
    # but must retain the original Bother processing workflow.
    use_corner_warp = corners is not None
    
    # print(f"[DEBUG] corners argument supplied: {corners is not None}")
    # print(f"[DEBUG] legacy bounds argument supplied: {bounds is not None}")
    # print(f"[DEBUG] use_corner_warp: {use_corner_warp}")
    # print(f"[DEBUG] scale_image: {scale_image}")

    if corners is not None:
        if scale_image is None:
            error(
                'corners requires scale_image to specify the output '
                'raster dimensions.'
            )

        normalized_corners = _validate_corners(corners)


    elif bounds is not None:
        # -------------------------------------------------------------------
        # LEGACY COMPATIBILITY:
        # Keep bounds for now, but explicitly warn that it is going away and
        # only reliably describes north-oriented boxes.
        # -------------------------------------------------------------------

        warnings.warn(
            'bounds is deprecated and will be removed in a future version. '
            'Use corners instead. bounds only supports north-oriented '
            'axis-aligned bounding boxes; rotated or otherwise non-axis-'
            'aligned bounds may produce unintended results.',
            DeprecationWarning,
            stacklevel=2,
        )

        print(
            'WARNING: bounds is deprecated and will be removed in a future '
            'version. Use corners instead.'
        )
        print(
            'WARNING: bounds requires a north-oriented, axis-aligned '
            'bounding box to work properly. Rotated or otherwise '
            'non-axis-aligned bounds may produce unintended results.'
        )

        if isinstance(bounds, list):
            if len(bounds) != 4:
                error('bounds must be a list of 4 values.')

            normalized_corners = _bounds_to_corners(bounds)

        elif isinstance(bounds, gpd.GeoDataFrame):
            if bounds.crs != 'EPSG:4326':
                raise ValueError(
                    'Input GeoDataframe must use CRS EPSG 4326.'
                )

            if len(bounds) > 1:
                raise ValueError(
                    'Only 1 boundary feature can be processed at a time. '
                    + str(len(bounds))
                    + ' features provided.'
                )

            geometry = bounds.geometry.iloc[0]

            # Legacy bounds behavior is deliberately retained here:
            # use the geometry's axis-aligned bounding box.
            minx, miny, maxx, maxy = geometry.bounds

            normalized_corners = _bounds_to_corners(
                [miny, minx, maxy, maxx]
            )

        elif isinstance(bounds, str):
            ext = os.path.splitext(
                os.path.basename(bounds)
            )[1].lower()

            if ext != '.shp':
                raise ValueError(
                    'Input file path must be a shapefile.'
                )

            bounds_gdf = gpd.read_file(bounds)

            if bounds_gdf.crs != 'EPSG:4326':
                raise ValueError(
                    'Input GeoDataframe must use CRS EPSG 4326.'
                )

            if len(bounds_gdf) > 1:
                raise ValueError(
                    'Only 1 boundary feature can be processed at a time. '
                    + str(len(bounds_gdf))
                    + ' features provided.'
                )

            geometry = bounds_gdf.geometry.iloc[0]

            minx, miny, maxx, maxy = geometry.bounds

            normalized_corners = _bounds_to_corners(
                [miny, minx, maxy, maxx]
            )  
    
    
    
    # -----------------------------------------------------------------------
    # Defaults
    # -----------------------------------------------------------------------
    
    '''
    Set defaults if params given as boolean
    '''
    if lakes == True:
        lakes = 80
        
    if raise_undersea == True:
        raise_undersea == 1
        
    if raise_low == True:
        raise_low = 0.0
    
    
    # -----------------------------------------------------------------------
    # Validate EPSG.
    # -----------------------------------------------------------------------

    try:
        CRS.from_epsg(epsg)
    except CRSError:
        print('WARNING: Input EPSG code is invalid. Defaulting to 4326')
        epsg = '4326'

    destination_crs = f'EPSG:{epsg}'

    # -----------------------------------------------------------------------
    # Get source DEM.
    # -----------------------------------------------------------------------

    tmp_file = None

    if normalized_corners is not None:

        # ---------------------------------------------------------------
        # CORNER WORKFLOW:
        # Always use a temporary file for the north-up source DEM.
        #
        # outfile_tif is reserved for the final, warped output raster.
        # ---------------------------------------------------------------
    
        if use_corner_warp:
            to_file = os.path.join(
                tempfile.gettempdir(),
                f'otter_source_{time.time()}.tif',
            )
            tmp_file = to_file
    
        elif outfile_tif:
            # Preserve existing legacy bounds behavior.
            to_file = os.path.abspath(outfile_tif)
    
        else:
            to_file = os.path.join(
                tempfile.gettempdir(),
                f'othg_{time.time()}.tif',
            )
            tmp_file = to_file
    
        left, bottom, right, top = _corners_to_enclosing_bounds(
            normalized_corners
        )
    
        tif_file = create_tif_file(
            left,
            bottom,
            right,
            top,
            to_file,
        )
    
    else:
        tif_file = infile_tif
        

    if tif_file:
        with open(tif_file, 'rb') as f:
            memfile = MemoryFile(f)

        with memfile.open() as msrc:
            msrc_crs = msrc.crs

        if scale_data is not None:
            memfile = resample(memfile, scale_data)

        if no_sea:
            memfile = remove_sea(memfile)

        # -------------------------------------------------------------------
        # ROTATION:
        # For a corners-based map, explicitly construct the destination
        # transform and raster dimensions.
        #
        # For legacy bounds, retain the existing north-up behavior.
        # -------------------------------------------------------------------

        if use_corner_warp and scale_image:
            # print("[DEBUG] Using quadrilateral warp")
            memfile = _warp_quadrilateral_raster(
                memfile=memfile,
                corners=normalized_corners,
                width=map_width,
                height=map_height,
                dst_crs=destination_crs,
            )

        elif (
            epsg
            and (epsg != str(WGS84))
            or (msrc_crs != WGS84)
        ):
            memfile = reproject_raster(
                memfile,
                dst_crs=destination_crs,
            )

        if lakes:
            memfile = set_lakes_to_elev(memfile, lakes)

        if raise_undersea is not None:
            memfile = raise_undersea_land(
                memfile,
                raise_undersea,
            )

        if raise_low is not None:
            memfile = raise_low_pixels(
                memfile,
                raise_low,
                max_brightness,
            )
            
        # ---------------------------------------------------------------
        # CORNER WORKFLOW:
        # Save the final warped raster, not the original north-up
        # SRTM source raster.
        #
        # The destination CRS remains EPSG:4326 for compatibility
        # with the rest of Otter.
        # ---------------------------------------------------------------
    
        if use_corner_warp and outfile_tif:
            memfile.seek(0)
    
            with open(outfile_tif, 'wb') as output_file:
                output_file.write(memfile.read())

        im = to_png(
            memfile,
            not raise_low,
            max_brightness,
        )

    elif infile_png:
        im = Image.open(infile_png)

    # -----------------------------------------------------------------------
    # Legacy crop/scale operations.
    #
    # ROTATION:
    # For corners-based maps, scale_image is already applied during raster
    # reprojection. Do not resize it again.
    # -----------------------------------------------------------------------

    if crop:
        res, mode = crop
        res = res.split('x')
        width = int(res[0])
        height = int(res[1])
        im = crop_image(im, width, height, mode)

    # Existing behavior for non-corners workflows.
    if scale_image and not use_corner_warp:
        print("[DEBUG] Using legacy PNG scaling")
        im = scale_image_f(
            im,
            map_width,
            map_height,
        )

    if outfile.endswith('.png'):
        save_to = outfile
    else:
        save_to = outfile + '.png'

    try:
        png_to_file(im, save_to)
    except FileNotFoundError:
        error(
            f'Could not save to {save_to}. '
            'Check that the directory to which you want to save exists.'
        )

    if tmp_file:
        os.remove(tmp_file)

    if clear_cache:
        clear_cache()