'''
This script contains a function to edit the game map (in raster form) to
set rivers and lakes to sea level.
This is designed for water features that are near sea-level and would not create
strange adjacent terrain. 

This is an advanced feature requring basic GIS knowledge.
'''

'''
TODO:
    - add support for inputs like in get_map_coords
    - add checks for CRS; currently assumes same CRS
    - add option to create buffer around given features of set size
'''

import math
import rasterio as rio
import rasterio.mask
import fiona
import geopandas as gpd
import numpy as np
import warnings

def add_water(
    ras,
    shp_path,
    outpath,
    select_col=None,
    select_val=None,
    buffer=None,
):
    '''
    This function edits a raster by setting rivers and lakes to sea-level.

    Parameters
    ----------
    **ras** : *str, path*
        Path to a raster file from georeferenced png output from bother.

    **shp_path** : *str, path*
        Path to a shapefile containing river delineations or lake polygons.

    **outpath** : *str, path*
        Path to write a new tif.

    **select_col** : *str*
        Column name to filter values.

    **select_val** : *str, int, float*
        Value used to filter values in select_col.

    **buffer** : *int*
        If provided, creates a buffer around the input shapes of the
        indicated number of game-grid tiles.

    Returns
    -------
    None.
    '''
    
    print('Reading shapefile...')

    df = gpd.read_file(shp_path)

    if select_col is not None:
        print('Filtering rows...')
        df = df.loc[df[select_col] == select_val]

    water_shapes = df['geometry'].values.tolist()

    print('Reading raster...')

    with rio.open(ras) as src:
        # -------------------------------------------------------------------
        # ROTATION:
        # A general affine transform is:
        #
        #     x = a * col + b * row + c
        #     y = d * col + e * row + f
        #
        # Therefore:
        #
        #     column/pixel vector = (a, d)
        #     row/pixel vector    = (b, e)
        #
        # Their magnitudes give the physical dimensions of the two raster
        # axes even when the raster is rotated.
        # -------------------------------------------------------------------

        transform = src.transform

        pixel_x = math.hypot(
            transform.a,
            transform.d,
        )

        pixel_y = math.hypot(
            transform.b,
            transform.e,
        )

        if buffer is not None:
            if not math.isclose(
                pixel_x,
                pixel_y,
                rel_tol=1e-9,
                abs_tol=1e-12,
            ):
                warnings.warn(
                    'Pixel x and y dimensions do not match. '
                    'Using average for buffer.'
                )

                buff_dist = (
                    (pixel_x + pixel_y) / 2
                ) * buffer
            else:
                buff_dist = pixel_x * buffer

            # Suppress the GeoPandas geographic-CRS buffer warning here
            # because the distance was explicitly derived from the raster's
            # CRS units.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')

                buff_geo = df['geometry'].buffer(
                    buff_dist,
                    cap_style='square',
                )

            water_shapes = buff_geo.tolist()

        arr = src.read()

        out_image, out_transformation = rio.mask.mask(
            src,
            water_shapes,
            crop=False,
        )

        out_meta = src.meta

    print('Setting water to sea-level...')

    water_cells_idx = ~np.isnan(out_image)

    arr[water_cells_idx] = 0

    print('Writing edited raster...')

    with rio.open(
        outpath,
        'w',
        driver='GTiff',
        height=out_meta['height'],
        width=out_meta['width'],
        count=1,
        dtype=out_meta['dtype'],
        crs=out_meta['crs'],
        nodata=out_meta['nodata'],
        transform=out_meta['transform'],
    ) as dst:
        dst.write(arr)

    print('Done.')