'''
This script contains a function to convert row,col indices from a scaled map to
real-world latitude and longitude.

'''

'''
TODO:
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


def get_latlong_from_map(ras, grid_coords, outpath=None, row_col=None, col_col=None,
                         select_col=None, select_val=None):
    '''
    This function finds lat,long coords given row,col grid indices from a OTTD map.
    Longitude is the X coordinate (column)
    Latitude is the Y coordinate (row)

    Parameters
    ----------
    ras : str, path
        path to a raster created from georeferencing the png output of bother.
    grid_coords : str, dataframe, geodataframe, list
        Path to a shapefile, CSV, or excel file or a dataframe or geodataframe or a list of row,col pairs
    outpath : str, path
        path to an ouput csv or excel file or shapefile to write the lat,long coords
    row_col : str, optional
        name of the column containing the row value. The default is None.
    col_col : str, optional
        name of the column containing the column value. The default is None.
    select_col : str
        column name to filter values
    select_val : str, int, float
        value used to fitler values in select_col

    Returns
    -------
    Dataframe with long,lat coordinates

    '''
    
    
    
    
    shp_path = False
    csv_path = False
    excel_path = False
    df_input = False
    gdf_input = False
    rc_input = False
    
    ## check inputs type of grid_coords to determine which logic route to take
    if isinstance(grid_coords, str):
        
        if not os.path.isfile(grid_coords):
            raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of row,col pairs')
        
        ext = os.path.splitext(os.path.basename(grid_coords))[1]
        if ext == '.shp':
            shp_path = True
        elif (ext == '.csv') or (ext == '.txt'):
            csv_path = True
        elif ext == '.xlsx':
            excel_path = True
        else:
            raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of grid_coords pairs')
    
    elif isinstance(grid_coords, pd.DataFrame):
        df_input = True
    
    elif isinstance(grid_coords, gpd.GeoDataFrame):
        gdf_input = True
    
    elif isinstance(grid_coords, list):
        rc_input = True
    
    else:
        raise ValueError('coords must be a valid shapefile, CSV or Excel file, dataframe, or list of grid_coords pairs')
    
        
    
    print('Reading input data...')

    ## route for CSV files
    if csv_path:
        df = pd.read_csv(grid_coords, encoding_errors='ignore')
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
            
        tile_coords = list(zip(df[row_col],df[col_col]))
        
        
    ## route for excel files
    if excel_path:
        df = pd.read_excel(grid_coords)
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]

        tile_coords = list(zip(df[row_col],df[col_col]))
        
        
    ## route for shapefiles    
    if shp_path:
        df = gpd.read_file(grid_coords)
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
        tile_coords = list(zip(df[row_col],df[col_col]))
        

    ## route for dataframes
    if df_input:
        df = grid_coords
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
            
        tile_coords = list(zip(df[row_col],df[col_col]))
    
    
    ## route for geodataframes
    if gdf_input:
        df = grid_coords
        if select_col is not None:
            print('Filtering rows...')
            df = df.loc[df[select_col] == select_val]
            
        tile_coords = list(zip(df[row_col],df[col_col]))


    ## route for lists
    if rc_input:
        df = pd.DataFrame(grid_coords,columns=['row','col'])

        tile_coords = list(zip(df['row'],df['col']))
    
    
    ## create grids of latitude and longitude for raster pixels
    with rio.open(ras) as src:
        arr = src.read()
        h = arr.shape[1]
        w = arr.shape[2]
        ras_cols, ras_rows = np.meshgrid(np.arange(w), np.arange(h))
        xs, ys = rio.transform.xy(src.transform, ras_rows, ras_cols)
        longs = np.array(xs).reshape((h,w))
        lats = np.array(ys).reshape((h,w))
        
    ## match latitude and longitude with provided tile coordinates
    long_list = [None]*len(tile_coords)
    lat_list = [None]*len(tile_coords)
    
    for i in tqdm(range(len(tile_coords)), position=0, leave=True):
        t = tile_coords[i]
        r = t[0]
        c = t[1]
        long = longs[r,c]
        lat = lats[r,c]
        long_list[i] = long
        lat_list[i] = lat
        
    df['latitude'] = lat_list
    df['longitude'] = long_list
    
    if outpath is not None:
        print('Writing to file...')
        if os.path.splitext(os.path.basename(outpath))[1] == '.csv':
            df.to_csv(outpath, index=False)
            
        if os.path.splitext(os.path.basename(outpath))[1] == '.xlsx':
            df.to_excel(outpath, index=False)
        
        if os.path.splitext(os.path.basename(outpath))[1] == '.shp':
            geometry = [Point(xy) for xy in zip(df.longitude, df.latitude)]
            gdf = gpd.GeoDataFrame(df, geometry=geometry)
            gdf.crs = 'EPSG:4326'
            gdf.to_file(outpath, driver='ESRI Shapefile')
    
    print('Done.')
        
    return df    
        
        