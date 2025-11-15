'''
This script contains a function to extract the row,col indices from a scaled map.
This function can be used to find the row,col indices on the game map for towns
and industries using real-world coordinates.

The OTTD grid coordinate system has the same origin as numpy data arrays
where the top left is 0,0. Therefore, raster array rows coorespond with
OTTD X coordinates and columns correspond with OTTD Y coordinates (clockwise orientation)

'''

'''
TODO:
    - return nearest land point if point on water
    - replace loop with something more efficient
    - add checks for shapefile CRS
    
'''


import os
import rasterio as rio
import rasterio.mask
import numpy as np
# import fiona
from tqdm import tqdm
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import warnings


def get_map_coords(ras, coords, outpath=None, lat_col=None, long_col=None, 
                   select_col=None, select_val=None):
    '''
    This function finds row,col indicies (clockwise) of OTTD maps from given lat-long coordinates.

    Parameters
    ----------
    **ras** : *str, path*;
        path to a raster created from georeferencing the png output of bother.
        
    **coords** : *str, dataframe, geodataframe, list*
        Path to a shapefile, CSV, or excel file or a dataframe or geodataframe or a list of longtitude-latitude pairs
        
    **outpath** : *str, path*;
        path to an ouput csv or excel file to write the row,col indices to
        
    **lat_col** : *str, optional*;
        name of the column containing the latitude. The default is None.
        
    **long_col** : *str, optional*;
        name of the column containing the longitude. The default is None.
        
    **select_col** : *str*;
        column name to filter values
        
    **select_val** : *str, int, float*;
        value used to fitler values in select_col

    Returns
    -------
    Dataframe with game-grid row,col indices (clockwise)

    '''
    
    shp_path = False
    csv_path = False
    excel_path = False
    gdf_input = False
    df_input = False
    long_lat = False
    
    ## check inputs type of coords to determine which logic route to take
    if isinstance(coords, str):
        
        if not os.path.isfile(coords):
            raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of longitude-latitude pairs')
        
        ext = os.path.splitext(os.path.basename(coords))[1]
        if ext == '.shp':
            shp_path = True
        elif (ext == '.csv') or (ext == '.txt'):
            csv_path = True
        elif ext == '.xlsx':
            excel_path = True
        else:
            raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of longitude-latitude pairs')
    
    ## need to check for gdf first because gdf is also a df
    elif isinstance(coords, gpd.GeoDataFrame):
        gdf_input = True
    
    elif isinstance(coords, pd.DataFrame):
        df_input = True
    
    elif isinstance(coords, list):
        long_lat = True
    
    else:
        raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of longitude-latitude pairs')
    
        
    
    print('Reading input data...')

    ## route for CSV files
    if csv_path:
        df = pd.read_csv(coords, encoding_errors='ignore')
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        try:
            shapes = [Point(xy) for xy in zip(df[long_col], df[lat_col])] # shapely Points
        except:
            raise Exception('Error occured when converting lat-long to points. Check that the data is correct.')
        
    ## route for excel files
    if excel_path:
        df = pd.read_excel(coords)
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        try:
            shapes = [Point(xy) for xy in zip(df[long_col], df[lat_col])] # shapely Points
        except:
            raise Exception('Error occured when converting lat-long to points. Check that the data is correct.')
        
    ## route for shapefiles    
    if shp_path:
        df = gpd.read_file(coords)
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        shapes = df['geometry'].values.tolist()

    ## route for geodataframes
    if gdf_input:
        df = coords
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        shapes = df['geometry'].values.tolist()

    ## route for dataframes
    if df_input:
        df = coords
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        try:
            shapes = [Point(xy) for xy in zip(df[long_col], df[lat_col])] # shapely Points
        except:
            raise Exception('Error occured when converting lat-long to points. Check that the data is correct.')
    

    ## route for lists
    if long_lat:
        df = pd.DataFrame(coords,columns=['long','lat'])
        try:
            df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['long'],df['lat']))
        except:
            raise Exception('Error occured when converting lat-long to points. Check that the data is correct.')
        shapes = df['geometry'].values.tolist()
    
    
    
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
    water = [0]*len(shapes) # flat for water
    multi = [None]*len(shapes) # flag for multiple tile coords given for the feature
    
    with rio.open(ras) as src:
        for i in tqdm(range(len(shapes)), position=0, leave=True):
            s = shapes[i]
            ## check for empty points
            if (s.is_empty) or (not s.is_valid):
                continue
            s = [s]
            out_image, out_transformation = rio.mask.mask(src, s, crop=False) # nan where not overlapping
            idx = ~np.isnan(out_image) # find where not 0
            
            if not idx.any():
                warnings.warn('Point outside of map. Skipping.')
                continue
            
            if 0 in out_image:
                warnings.warn('Point on water. Flagging.')
                water[i] = 1
                
            idx_rc = np.argwhere(idx) # where is idx true
            
            if len(idx_rc) > 1:
                multi_rows = idx_rc[:,1].tolist()
                multi_rows = [x+1 for x in multi_rows]
                multi_cols = idx_rc[:,2].tolist()
                multi_cols = [x+1 for x in multi_cols]
                row[i] = multi_rows
                col[i] = multi_cols
                multi[i] = 1
            elif len(idx_rc) == 1:
                # top left corner is 1,1 in OTTD. 
                # in GIS, top left corner is 0,0. Need to add 1 to all coordinates
                row[i] = idx_rc[0,1] + 1 
                col[i] = idx_rc[0,2] + 1
                multi[i] = 0
            else:
                warnings.warn('No intersection with map. Skipping.')
                continue
    
    
    ## Create unique column names to avoid overwriting existing columns
    ## but the user will need to know which is the right column set to use
    cols_to_add = ['row','col','water','multi']
    for c in list(range(len(cols_to_add))):
        cta = cols_to_add[c]
        i=1
        while cta in df.columns:
            cta = cta + '.' + str(i)
            i=i+1
        cols_to_add[c] = cta
        
    df[cols_to_add[0]] = row
    df[cols_to_add[1]] = col
    df[cols_to_add[2]] = water
    df[cols_to_add[3]] = multi
    
    if outpath is not None:
        print('Writing to file...')
        if os.path.splitext(os.path.basename(outpath))[1] == '.csv':
            df.to_csv(outpath, index=False)
            
        if os.path.splitext(os.path.basename(outpath))[1] == '.xlsx':
            df.to_excel(outpath, index=False)
            
        if os.path.splitext(os.path.basename(outpath))[1] == '.shp':
            geometry = shapes
            gdf = gpd.GeoDataFrame(df, geometry=geometry)
            gdf.crs = 'EPSG:4326'
            gdf.to_file(outpath, driver='ESRI Shapefile')
    
    print('Done.')
    
    return df
