'''
This script contains a function to edit the game map (in raster form) to convert water to land.

This is an advanced feature requring basic GIS knowledge.
'''

'''
TODO:
    - add support for non-shapefile inputs
    - add checks for CRS; currently assumes same CRS
'''

import rasterio as rio
import fiona


def add_land(ras, shp_path, outpath, elevation=1):
    '''
    This function edits a raster by setting water to land.

    Parameters
    ----------
    ras : str, path
        path to a raster file from georeferenced png output from bother OR an original data raster.
    shp_path : str, path
        path to a shapefile containing river delineations or lake polygons.
    outpath : str, path
        path to write a new tif.
    elevation : int, float
        1-255 for grayscale to edit scaled outputs from bother; if editting data rasters, rerun through bother to convert to grayscale

    Returns
    -------
    None.

    '''
    
    print('Reading shapefile...')
    # open shapefile and gather features
    with fiona.open(shp_path, 'r') as shapefile:
        # shp_crs = shapefile.crs
        land_shapes = [feature['geometry'] for feature in shapefile]
        
    print('Reading raster...')
    with rio.open(ras) as src:
        # ras_crs = src.crs
        out_image, out_transformation = rio.mask.mask(src, land_shapes, crop=False, nodata=0) # nodata defaults to 0, this is fine
        out_meta = src.meta
        
    print('Setting rivers to sea-level...')
    land_cells_idx = out_image == 0 # get cells that are 0
    out_image[land_cells_idx] = elevation # set cells to 0
    
    print('Writing editted raster...')
    with rio.open(outpath,'w') as dest:
        dest.meta = out_meta
        
    print('Done.')