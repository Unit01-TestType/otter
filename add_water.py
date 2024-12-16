'''
This script contains a function to edit the game map (in raster form) to
set rivers and lakes to sea level.
This is designed for water features that are near sea-level and would not create
strange adjacent terrain. 

This is an advanced feature requring basic GIS knowledge.
'''

'''
TODO:
    - add support for non-shapefile inputs
    - add checks for CRS; currently assumes same CRS
'''

import rasterio as rio
import fiona


def add_water(ras, shp_path, outpath):
    '''
    This function edits a raster by setting rivers and lakes to sea-level.

    Parameters
    ----------
    ras : str, path
        path to a raster file from georeferenced png output from bother.
    shp_path : str, path
        path to a shapefile containing river delineations or lake polygons.
    outpath : str, path
        path to write a new tif.

    Returns
    -------
    None.

    '''
    
    print('Reading shapefile...')
    # open shapefile and gather features
    with fiona.open(shp_path, 'r') as shapefile:
        # shp_crs = shapefile.crs
        water_shapes = [feature['geometry'] for feature in shapefile]
        
    print('Reading raster...')
    with rio.open(ras) as src:
        # ras_crs = src.crs
        out_image, out_transformation = rio.mask.mask(src, water_shapes, crop=False, nodata=0) # nodata defaults to 0, this is fine
        out_meta = src.meta
        
    print('Setting rivers to sea-level...')
    water_cells_idx = out_image != 0 # get cells not already set to 0
    out_image[water_cells_idx] = 0 # set cells to 0
    
    print('Writing editted raster...')
    with rio.open(outpath,'w') as dest:
        dest.meta = out_meta
        
    print('Done.')