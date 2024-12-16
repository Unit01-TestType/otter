'''
This script contains a function to extract the row,col indices from a scaled map.
This function can be used to find the row,col indices on the game map for towns
and industries using real-world coordinates.
'''

'''
TODO:
    - add support for shapefiles and raw coordinates
    - allow for discrete points, linear features, and polygons
        - extract indices for all tiles overlapping linear features
        - polygons: param for defining polygon vertices and bounding box or shapefile
    - replace loop with something more efficient
    - add checks for shapefile CRS
'''


import os
import rasterio as rio
import rasterio.mask
import numpy as np
import fiona
from tqdm import tqdm
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import warnings


def get_map_coords(ras, outpath, shp_path=None, csv_path=None, lat_col=None, long_col=None):
    '''
    This function finds row,col indicies of OTTD maps from given lat-long coordinates.

    Parameters
    ----------
    ras : str, path
        path to a raster created from georeferencing the png output of bother.
    outpath : str, path
        path to an ouput csv or excel file to write the row,col indices to
    shp_path : str, path, optional
        path to a shapefile containing point features of interest. The default is None.
    csv_path : str, path, optional
        path to an excel or csv file containing point coordinates. The default is None.
    lat_col : str, optional
        name of the column containing the latitude in the csv or excel file. The default is None.
    long_col : str, optional
        name of the column containing the longitude in the csv or excel file. The default is None.

    Returns
    -------
    None.

    '''
    
    if (shp_path is None) and (csv_path is None):
        raise ValueError('Must provide shp_path or csv_path to a valid shapefile or CSV or Excel file')
    
    if (shp_path is not None) and (csv_path is not None):
        raise warnings.warn('both shp_path and csv_path provided; using shp_path')
        
    '''
    Route for CSV and Excel files.
    Convert lat-long to geometry.
    '''
    
    print('Reading input data...')
    
    if shp_path is None:
        
        if os.path.splitext(os.path.basename(csv_path))[1] == '.csv':
            df = pd.read_csv(csv_path, encoding_errors='ignore')
           
        elif os.path.splitext(os.path.basename(csv_path))[1] == '.xlsx':
            df = pd.read_excel(csv_path)
        
        
        if (lat_col is None) or (long_col is None):
            raise ValueError('must provide lat_col and lat_col when using excel or csv')
        
        if lat_col not in df:
            raise ValueError('lat_col not a valid column name')
        if long_col not in df:
            raise ValueError('long_col not a valid column name')
        
        try:
            shapes = [Point(xy) for xy in zip(df[long_col], df[lat_col])] # shapely Points
            # df['geometry'] = shapes
        except:
            raise Exception('Error occured when converting lat-long to points. Check that the data is correct.')
    
    
    # '''
    # Route for shapefiles.
    # Read geometry directly.
    # '''
    elif shp_path is not None:
        
        with fiona.open(shp_path, 'r') as shapefile:
            shapes = [feature['geometry'] for feature in shapefile]
            
        df = gpd.read_file(shp_path)
        
    
    
    '''
    Open and read raster file and mask with points.
    This should keep only the overlapping pixel to each point.
    For linear features or polygons, multiple tiles are retured as a list and the feature is flagged.
    Additional post-processing may be needed for lines and polygons.
    The loop may be ineffcient, but it works to keep track of coordinates for each point.
    '''
    
    print('Extracting row,col indices...')
    ## empty placeholder lists to store indices
    row = [None]*len(shapes)
    col = [None]*len(shapes)
    water = [None]*len(shapes) # flat for water
    multi = [None]*len(shapes) # flag for multiple tile coords given for the feature
    
    with rio.open(ras) as src:
        for i in tqdm(range(len(shapes)), position=0, leave=True):
            s = [shapes[i]]
            out_image, out_transformation = rio.mask.mask(src, s, crop=False) # nodata defaults to 0, this is fine
            idx = np.argwhere(out_image)
            if not out_image.any():
                warnings.warn('Point on water or outside of map. Flagging.')
                water[i] = 1
            if len(idx) != 0:
                # top left corner is 1,1 in OTTD. 
                # in GIS, top left corner is 0,0. Need to add 1 to all coordinates
                water[i] = 0
            elif len(idx) > 1:
                multi_rows = idx[:,1].tolist()
                multi_rows = [x+1 for x in multi_rows]
                multi_cols = idx[:,2].tolist()
                multi_cols = [x+1 for x in multi_cols]
                row[i] = multi_rows
                col[i] = multi_cols
                multi[i] = 1
            else:
                row[i] = idx[0,1] + 1 
                col[i] = idx[0,2] + 1
                multi[i] = 0
    
    df['row'] = row
    df['col'] = col
    df['water'] = water
    df['multi'] = multi
    
    print('Writing to file...')
    if os.path.splitext(os.path.basename(outpath))[1] == '.csv':
        df.to_csv(outpath, index=False)
        
    if os.path.splitext(os.path.basename(outpath))[1] == '.xlsx':
        df.to_excel(outpath, index=False)
    
    print('Done.')
    
    return df
