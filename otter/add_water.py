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

import rasterio as rio
import rasterio.mask
import fiona
import geopandas as gpd
import numpy as np
import warnings

def add_water(ras, shp_path, outpath, select_col=None, select_val=None, buffer=None):
    '''
    This function edits a raster by setting rivers and lakes to sea-level.

    Parameters
    ----------
    **ras** : *str, path*;
        path to a raster file from georeferenced png output from bother.
        
    **shp_path** : *str, path*;
        path to a shapefile containing river delineations or lake polygons.
        
    **outpath** : *str, path*;
        path to write a new tif.
        
    **select_col** : *str*;
        column name to filter values
        
    **select_val** : *str, int, float*;
        value used to fitler values in select_col
        
    **buffer** : *int*;
        If provided, creates a buffer around the inputs shapes of the indicated number of tiles.

    Returns
    -------
    None.

    '''
    
    print('Reading shapefile...')
    # open shapefile and gather features
    # with fiona.open(shp_path, 'r') as shapefile:
    #     # shp_crs = shapefile.crs
    #     water_shapes = [feature['geometry'] for feature in shapefile]
    df = gpd.read_file(shp_path)
    
    if select_col is not None:
        print('Filtering rows...')
        df = df.loc[df[select_col] == select_val]
        
    water_shapes = df['geometry'].values.tolist()
        
    print('Reading raster...')
    with rio.open(ras) as src:
        # ras_crs = src.crs
        pixel_x = src.transform[0] # pixel x dimension in crs units
        pixel_y = src.transform[4] # pixel y diemension in crs units
        
        if buffer is not None:
            if abs(pixel_x) != abs(pixel_y):
                warnings.warn("Pixel x and y dimensions do not match. Using average for buffer")
                buff_dist = ((abs(pixel_x)+abs(pixel_y))/2) * buffer
            else:
                buff_dist = pixel_x * buffer
            
            ## suppress the buffer CRS warning
            ## since we're grabbing the correct distance from the raster
            warnings.filterwarnings('ignore')
            ## create the buffer
            buff_geo = df['geometry'].buffer(buff_dist, cap_style='square')
            water_shapes = buff_geo.tolist()
        
        arr = src.read()
        out_image, out_transformation = rio.mask.mask(src, water_shapes, crop=False) # returns only values underlaying feature, otherwise 0
        out_meta = src.meta
        
    print('Setting water to sea-level...')
    water_cells_idx = ~np.isnan(out_image)
    arr[water_cells_idx] = 0 # set cells to 0
    
    print('Writing editted raster...')
    with rio.open(outpath, 
                  'w',
                  driver='GTiff',
                  height=out_meta['height'],
                  width=out_meta['width'],
                  count=1,#numebr of bands
                  dtype=out_meta['dtype'],
                  crs=out_meta['crs'],
                  nodata=out_meta['nodata'], # change if data has nodata value
                  transform=out_transformation) as dst:
        
        dst.write(arr)
        
    print('Done.')