'''
This script contains an adaptation of bother by bunburya for to work with otter to retrieve terrain data
and create a png and tif raster for the heightmap.

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

from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError

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

# EPSG codes
WGS84 = 4326  # Mercator - The default CRS used in the STRM data
PSEUDO_MERCATOR = 3857  # Web Mercator - The projection used by Google Maps, OpenStreetMap, etc.

def error(msg: str):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# ROTATION:
# New helpers for converting the old bounds representation into the new
# four-corner representation and validating oriented rectangles.
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
    Project corners into a local UTM CRS for geometric validation.

    The user-facing coordinates remain WGS84. This projection is only used
    to determine whether the supplied points form a rectangle and whether
    its physical aspect ratio is correct.
    """
    mean_lat = sum(c[0] for c in corners) / 4
    mean_lon = sum(c[1] for c in corners) / 4

    zone = int((mean_lon + 180) / 6) + 1

    if mean_lat >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    transformer = Transformer.from_crs(
        'EPSG:4326',
        f'EPSG:{epsg}',
        always_xy=True,
    )

    # Return x,y rather than lat,lon.
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


def _validate_corners(corners, map_width=None, map_height=None):
    """
    Validate that four supplied corners describe a rectangle.

    The aspect-ratio check is performed after projection into a local metric
    CRS so that longitude/latitude degree lengths are not used directly.
    """
    corners = _normalize_corners(corners)

    projected = _project_corners_for_validation(corners)

    a, b, c, d = projected

    ab = _vector(a, b)
    bc = _vector(b, c)
    cd = _vector(c, d)
    da = _vector(d, a)

    lengths = [
        _length(ab),
        _length(bc),
        _length(cd),
        _length(da),
    ]

    if any(length == 0 for length in lengths):
        raise ValueError('corners must not contain duplicate points.')

    # Opposite sides must be parallel.
    if not _vectors_parallel(ab, cd):
        raise ValueError(
            'corners do not define a rectangle: first and third sides '
            'are not parallel.'
        )

    if not _vectors_parallel(bc, da):
        raise ValueError(
            'corners do not define a rectangle: second and fourth sides '
            'are not parallel.'
        )

    # Adjacent sides must be perpendicular.
    if not _vectors_perpendicular(ab, bc):
        raise ValueError(
            'corners do not define a rectangle: adjacent sides are not '
            'perpendicular.'
        )

    # Opposite sides should have equal lengths.
    tolerance = 1e-5

    if not math.isclose(
        lengths[0],
        lengths[2],
        rel_tol=tolerance,
        abs_tol=1e-3,
    ):
        raise ValueError(
            'corners do not define a rectangle: opposite side lengths '
            'do not match.'
        )

    if not math.isclose(
        lengths[1],
        lengths[3],
        rel_tol=tolerance,
        abs_tol=1e-3,
    ):
        raise ValueError(
            'corners do not define a rectangle: opposite side lengths '
            'do not match.'
        )

    # ROTATION:
    # If dimensions were supplied, enforce the OpenTTD map aspect ratio.
    if map_width is not None and map_height is not None:
        geographic_ratio = lengths[0] / lengths[1]
        map_ratio = map_width / map_height

        if not math.isclose(
            geographic_ratio,
            map_ratio,
            rel_tol=1e-4,
            abs_tol=1e-4,
        ):
            raise ValueError(
                f'The supplied corners have an aspect ratio of '
                f'{geographic_ratio:.6f}:1, but the requested map dimensions '
                f'{map_width}x{map_height} require an aspect ratio of '
                f'{map_ratio:.6f}:1.'
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

        The four points must form a rectangle. The rectangle may have any
        geographic orientation.

        When scale_image is supplied, its width/height ratio must match the
        physical aspect ratio of the supplied rectangle.

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

    if corners is not None:
        if scale_image is None:
            error(
                'corners requires scale_image so that the requested '
                'game-grid aspect ratio can be enforced.'
            )

        normalized_corners = _validate_corners(
            corners,
            map_width=map_width,
            map_height=map_height,
        )

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
        if outfile_tif:
            to_file = os.path.abspath(outfile_tif)
        else:
            to_file = os.path.join(
                tempfile.gettempdir(),
                f'othg_{time.time()}.tif',
            )
            tmp_file = to_file

        # -------------------------------------------------------------------
        # IMPORTANT:
        # SRTM only needs the enclosing axis-aligned rectangle. The actual
        # rotation is NOT applied here.
        # -------------------------------------------------------------------
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

        if normalized_corners is not None and scale_image:
            destination_transform = _make_destination_transform(
                normalized_corners,
                map_width,
                map_height,
                destination_crs,
            )

            memfile = reproject_raster(
                memfile,
                dst_crs=destination_crs,
                dst_transform=destination_transform,
                dst_width=map_width,
                dst_height=map_height,
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
    if scale_image and normalized_corners is None:
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