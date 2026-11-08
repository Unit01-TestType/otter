'''
This script contains an adaptation of bother by bunburya for to work with otter to retrieve terrain data
and create a png and tif raster for the heightmap.

This was heavily modified using ChatGPT to add support for rotated boundaries.

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
import rasterio

from pyproj import CRS, Geod, Transformer
from pyproj.exceptions import CRSError

from affine import Affine

from otter.bother_utils.srtm import create_tif_file#, clear_cache
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
    Warp an elevation raster onto an affine destination grid defined by
    four corners in map-grid order: TL, TR, BR, BL.

    The destination affine transform is used both to determine the
    geographic coordinates of output pixel centers and to georeference
    the resulting raster.

    The affine grid is constructed from TL, TR and BL. The discrepancy
    between its predicted BR and the supplied BR is measured and reported.

    Parameters
    ----------
    memfile : rasterio.io.MemoryFile
        Source elevation raster.
    corners : list
        Four (latitude, longitude) pairs in TL, TR, BR, BL order.
    width, height : int
        Destination raster dimensions.
    dst_crs : str or CRS
        Destination coordinate reference system.

    Returns
    -------
    rasterio.io.MemoryFile
        Warped elevation raster.
    """

    import warnings
    from pyproj import Transformer, Geod
    from scipy.ndimage import map_coordinates
    from rasterio.io import MemoryFile
    from affine import Affine

    if width <= 0 or height <= 0:
        raise ValueError("Raster dimensions must be greater than zero.")

    if len(corners) != 4:
        raise ValueError("Exactly four corners are required.")

    latitudes = np.asarray(
        [point[0] for point in corners],
        dtype=np.float64,
    )
    longitudes = np.asarray(
        [point[1] for point in corners],
        dtype=np.float64,
    )

    if not np.all(np.isfinite(latitudes)) or not np.all(
        np.isfinite(longitudes)
    ):
        raise ValueError("Corner coordinates must be finite.")

    if np.any(np.abs(latitudes) > 90):
        raise ValueError("Invalid latitude values.")

    # Transform the four corners into the requested destination CRS.

    wgs84_to_destination = Transformer.from_crs(
        "EPSG:4326",
        dst_crs,
        always_xy=True,
    )

    corner_x, corner_y = wgs84_to_destination.transform(
        longitudes,
        latitudes,
    )

    tl_x, tr_x, br_x, bl_x = corner_x
    tl_y, tr_y, br_y, bl_y = corner_y

    # Construct the destination affine transform.
    #
    # This defines the actual destination grid. Both sampling and output
    # georeferencing will use this exact transform.

    destination_transform = Affine(
        (tr_x - tl_x) / width,
        (bl_x - tl_x) / height,
        tl_x,
        (tr_y - tl_y) / width,
        (bl_y - tl_y) / height,
        tl_y,
    )

    # Check whether the supplied bottom-right corner agrees with the
    # parallelogram represented by the affine transform.

    predicted_br_x, predicted_br_y = destination_transform * (
        width,
        height,
    )

    destination_to_wgs84 = Transformer.from_crs(
        dst_crs,
        "EPSG:4326",
        always_xy=True,
    )

    actual_br_lon, actual_br_lat = destination_to_wgs84.transform(
        br_x,
        br_y,
    )

    predicted_br_lon, predicted_br_lat = destination_to_wgs84.transform(
        predicted_br_x,
        predicted_br_y,
    )

    geod = Geod(ellps="WGS84")

    _, _, br_error_m = geod.inv(
        actual_br_lon,
        actual_br_lat,
        predicted_br_lon,
        predicted_br_lat,
    )

    if br_error_m > 1.0:
        warnings.warn(
            "The supplied bottom-right corner does not exactly agree "
            "with the destination affine grid. "
            f"Discrepancy: {br_error_m:.3f} metres. "
            "The output raster will follow the affine grid defined by "
            "the other three corners.",
            UserWarning,
        )

    # Generate destination pixel-center coordinates using the affine
    # transform that will be written to the output raster.

    cols, rows = np.meshgrid(
        np.arange(width, dtype=np.float64) + 0.5,
        np.arange(height, dtype=np.float64) + 0.5,
    )

    destination_x, destination_y = destination_transform * (
        cols,
        rows,
    )

    # Convert destination coordinates into the source raster CRS.

    with memfile.open() as src:

        if src.crs is None:
            raise ValueError(
                "Source raster does not contain a CRS."
            )

        source_data = src.read(1).astype(np.float32)

        source_transform = src.transform
        source_crs = src.crs
        source_nodata = src.nodata

        destination_to_source = Transformer.from_crs(
            dst_crs,
            source_crs,
            always_xy=True,
        )

        source_x, source_y = destination_to_source.transform(
            destination_x,
            destination_y,
        )

        # Convert map coordinates into source pixel-center indices.

        inverse_transform = ~source_transform

        source_cols, source_rows = inverse_transform * (
            source_x,
            source_y,
        )

        source_cols -= 0.5
        source_rows -= 0.5

        # Identify valid source elevation pixels.

        valid = np.isfinite(source_data)

        if source_nodata is not None:
            if np.isnan(source_nodata):
                valid &= np.isfinite(source_data)
            else:
                valid &= source_data != source_nodata

        # Interpolate valid values and their validity weights separately.
        #
        # This prevents nodata values from contaminating valid elevations
        # during bilinear interpolation.

        valid_data = np.where(valid, source_data, 0.0).astype(
            np.float32
        )

        valid_weights = valid.astype(np.float32)

        coordinates = [
            source_rows.ravel(),
            source_cols.ravel(),
        ]

        sampled_values = map_coordinates(
            valid_data,
            coordinates,
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=False,
        ).reshape((height, width))

        sampled_weights = map_coordinates(
            valid_weights,
            coordinates,
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=False,
        ).reshape((height, width))

        # Restore nodata wherever no valid source data contributed.

        output_nodata = (
            source_nodata
            if source_nodata is not None
            else np.nan
        )

        warped_data = np.full(
            (height, width),
            output_nodata,
            dtype=np.float32,
        )

        valid_output = sampled_weights > 1e-6

        np.divide(
            sampled_values,
            sampled_weights,
            out=warped_data,
            where=valid_output,
        )

        # Prepare output raster metadata.

        profile = src.profile.copy()

        profile.update(
            driver="GTiff",
            width=width,
            height=height,
            count=1,
            dtype="float32",
            crs=dst_crs,
            transform=destination_transform,
            nodata=output_nodata,
        )

    # Write the resulting raster.

    output_memfile = MemoryFile()

    with output_memfile.open(**profile) as dst:
        dst.write(warped_data, 1)

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
    clear_cache=True,
):
    '''
    Run bother to download SRTM elevation data.

    Parameters
    ----------
    **outfile** : *str, path*
        The file to which the greyscale PNG image will be written.

    **bounds** : *list, GeoDataFrame, str, path*, optional
        Axis-aligned bounding box based on the original Bother --bounds argument.

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
        
    **clear_cache** : *boolean, optional*
        If True, clear the local Bother SRTM data cashe after running.
        Keeping the cache will reuse SRTM datasets for future runs rather than downloading
        the files for each run for the same overlapping area.

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
        # LEGACY BOTHER --BOUNDS COMPATIBILITY:
        # Keep bounds for now, but explicitly warn that it is going away and
        # only reliably describes north-oriented boxes.
        # -------------------------------------------------------------------

        warnings.warn(
            # 'bounds is deprecated and will be removed in a future version. '
            'bounds generally works best with north-oriented '
            'axis-aligned bounding boxes; rotated or otherwise non-axis-'
            'aligned bounds may produce unintended results.',
            DeprecationWarning,
            stacklevel=2,
        )

        # print(
        #     'WARNING: bounds is deprecated and will be removed in a future '
        #     'version. Use corners instead.'
        # )
        print(
            'WARNING: bounds works best with a north-oriented, axis-aligned '
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
        
        #### DEBUG TEMP
        with rasterio.open(tif_file) as src:
            print("\nSOURCE DEM")
            print("CRS:", src.crs)
            print("Bounds:", src.bounds)
            print("Transform:", src.transform)
            print("Dimensions:", src.width, src.height)
            print("Resolution:", src.res)
            print("Min/max:", src.read(1).min(), src.read(1).max())
        
        print("\nNORMALIZED CORNERS:")
        for corner in normalized_corners:
            print(corner)
        
        print("\nDESTINATION CRS:", destination_crs)
        print("MAP DIMENSIONS:", map_width, map_height)
    
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
            
            ### DEBUG TEMP
            # with memfile.open() as src:
            #     print("\nWARPED TIFF")
            #     print("CRS:", src.crs)
            #     print("Bounds:", src.bounds)
            #     print("Transform:", src.transform)
            #     print("Dimensions:", src.width, src.height)
            #     print("Resolution:", src.res)
            #     print("Min/max:", src.read(1).min(), src.read(1).max())

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
        # print("[DEBUG] Using legacy PNG scaling")
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