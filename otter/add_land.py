'''
This script contains a function to edit the game map (in raster form) to convert water to land.

This is an advanced feature requring basic GIS knowledge.
'''

'''
TODO:
    - add support for inputs like in get_map_coords
    - add checks for CRS; currently assumes same CRS
    - add option to create buffer around given features of set size
'''

import rasterio as rio
import rasterio.mask
# import fiona
import geopandas as gpd
import numpy as np


def add_land(ras, shp_path, outpath, elevation=1, select_col=None, select_val=None):
    '''
    This function edits a raster by setting land to water.

    Parameters
    ----------
    **ras** : *str, path*;
        path to a raster file from georeferenced png output from bother OR an original data raster.
        
    **shp_path** : *str, path*;
        path to a shapefile containing polygons for areas to convert to land.
        
    **outpath** : *str, path*;
        path to write a new tif.
        
   **elevation** : *int, float*;
        1-255 for grayscale to edit scaled outputs from bother; if editting data rasters, rerun through bother to convert to grayscale
        
    **select_col** : *str*;
        column name to filter values
        
    **select_val** : *str, int, float*;
        value used to fitler values in select_col

    Returns
    -------
    Writes GeoTIFF.

    '''
    
    print('Reading shapefile...')
    # open shapefile and gather features
    # with fiona.open(shp_path, 'r') as shapefile:
    #     # shp_crs = shapefile.crs
    #     land_shapes = [feature['geometry'] for feature in shapefile]
    df = gpd.read_file(shp_path)
    
    if select_col is not None:
        print('Filtering rows...')
        df = df.loc[df[select_col] == select_val]
        
    land_shapes = df['geometry'].values.tolist()
        
    print('Reading raster...')
    with rio.open(ras) as src:
        # ras_crs = src.crs
        arr = src.read()
        out_image, out_transformation = rio.mask.mask(src, land_shapes, crop=False)
        out_meta = src.meta
        
    print('Setting land to elevation...')
    land_cells_idx = ~np.isnan(out_image)
    arr[land_cells_idx] = elevation
    
    print('Writing editted raster...')
    with rio.open(outpath, 
                  'w',
                  driver='GTiff',
                  height=out_meta['height'],
                  width=out_meta['width'],
                  count=1, # numebr of bands
                  dtype=out_meta['dtype'],
                  crs=out_meta['crs'],
                  nodata=out_meta['nodata'], # change if data has nodata value
                  transform=out_transformation) as dst:
        
        dst.write(arr)
        
    print('Done.')