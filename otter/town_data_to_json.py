'''
This script contains a function to convert a simple pandas dataframe
to a .json file that can imported in the Scenario Builder to import
town data.

Rows coorespond with OTTD X coordinates (height) (clockwise orientation)
Columns correspond with OTTD Y coordinates (width) (clockwise orientation)

'''

'''
TODO:
    - add support for lists

'''

import os
import json
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'
import geopandas as gpd

def town_data_to_json(town_data, map_width, map_height, json_outfile,
                      name_field='name', pop_field='population', 
                      city_field='city', x_field='row', y_field='col',
                      select_col=None, select_val=None):
    '''
    This function converts town data from an input data format (e.g. pandas dataframe)
    to a .json file that can be used to import into the Scenario Builder.

    Parameters
    ----------
    **town_data** : *str, path, dataframe*;
        table of town data as a path to a shapefile, CSV, excel file or a pandas dataframe or geodataframe.
        
    **map_width** : *str, int*;
        width of the intended map to convert coordinates. OTTD maps are described as width x height.
        
    **map_height** : *str, int*;
        height of the inteded map to convert coordinates. OTTD maps are described as width x height.
        
    **json_outfile** : *str, path*;
        name and path to the output .json file with .json extension
        
    **name_field** : *str, optional*;
        name of the column defining the name of the town. The default is 'name'.
        
    **pop_field** : *str, optional*;
        name of the column defining the population. The default is 'population'.
        
    **city_field** : *str, optional*;
        name of the column defining the true/false flag for cities . The default is 'city'.
        
    **x_field** : *str, optional*;
        name of the column defining the x coordinate (height). The default is 'row'.
        
    **y_field** : *str, optional*;
        name of the column defining the y coordinate (width). The default is 'col'.
        
    **select_col** : *str*;
        column name to filter values
        
    **select_val** : *str, int, float*;
        value used to fitler values in select_col

    Returns
    -------
    Writes a .json file.

    '''
    
    
    ## check if file path to read CSV or excel
    if isinstance(town_data, str):
        
        if not os.path.isfile(town_data):
            raise ValueError('town_data must be a valid shapefile, CSV, Excel file, or pandas dataframe')
        
        ext = os.path.splitext(os.path.basename(town_data))[1]
        
        if ext == '.shp':
            town_data = gpd.read_file(town_data)
        
        elif ext == '.csv':
            town_data = pd.read_csv(town_data, encoding_errors='ignore')
                
        elif ext == '.xlsx':
            town_data = pd.read_excel(town_data)
                
        else:
            raise ValueError('town_data must be a valid shapefile, CSV, Excel file, or pandas dataframe')
    
    
    ## check if dataframe
    elif isinstance(town_data, pd.DataFrame):
        town_data = town_data
            
            
    ## check if geodataframe
    elif isinstance(town_data, gpd.GeoDataFrame):
        town_data = town_data

    
    else:
        raise ValueError('town_data must be a valid shapefile, CSV, Excel file, or pandas dataframe')
    
    
    
    
    ## filter rows for user-sepcified filtering
    if select_col is not None:
        print('Filtering rows...')
        town_data = town_data.loc[town_data[select_col] == select_val]
        
        
        
        
    ## filter rows to remove invalid row,col indices
    n_rows_before = len(town_data)
    town_data = town_data.dropna(subset=[x_field,y_field]) # drop where nan
    town_data = town_data.loc[ (town_data[x_field] > 0) & (town_data[x_field] <= int(map_height)) &
                               (town_data[y_field] > 0) & (town_data[y_field] <= int(map_width)) ]
    n_rows_after = len(town_data)
    if (n_rows_before - n_rows_after) > 0:
        print(str(n_rows_before - n_rows_after) + " rows with invalid row,col indices removed.")
    
    
    
    
    try:
        map_width = float(int(map_width))
    except:
        raise ValueError('map width must be a valid integer.')
    
    try:
        map_height = float(int(map_height))
    except:
        raise ValueError('map height must be a valid integer.')
    
    
    
    
    ## load data
    df = town_data[[name_field,pop_field,city_field,x_field,y_field]]
    
    ## rename columns to names used by OTTD
    df.columns = ['name','population','city','x','y']
    
    ## force population to be int
    df['population'] = df.loc[:,'population'].round(0).astype(int)
    
    ## convert x coordinate to proportional x coordinate
    df['x'] = df.loc[:,'x'].astype(float)
    df['x'] = df['x'] / map_height
    
    ## convert y coordinate to proportional y coordinate
    df['y'] = df.loc[:,'y'].astype(float)
    df['y'] = df['y'] / map_width
    
    
    ## convert to .json file
    with open(json_outfile, "w+") as f:
        json.dump(df.to_dict(orient='records'), f, indent=4)
    
    
    
    
    
    