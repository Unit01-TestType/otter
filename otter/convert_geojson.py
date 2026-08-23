'''
This script contains a function to convert the raw geojson output
from overpass turbo into geopandas dataframes, 
excel, csv, or shapefile for further editting
and manipulation.

https://overpass-turbo.eu/

Example query in overpass turbo to return cities and towns

[out:json][timeout:300];
// gather results
(
  node["place"="city"]({{bbox}});
  node["place"="town"]({{bbox}});
);
// print results
out geom;

'''

import os
import geopandas as gpd

def convert_geojson(geojson_path, outpath=None, cols=['name','population','longitude','latitude']):
    '''
    Covnert geojson output from overpass turbo into geopandas dataframes, 
    excel, csv, or shapefile.

    Parameters
    ----------
    **geojson_path** : *str*;
        Path to a geojson file.
        
    **outpath** : *str*;
        Path for the output file to write. File type is inferred from file extension. 
        If no path given, output will be geopandas dataframe.
        
    **cols** : *str*;
        Lsit of columns to keep in the output dataframe or file. Default: name, population, longitude, latitude
    
    Returns
    -------
    GeoDataFrame of converted geojson. If outpath provided, also writes to file.
    '''

    
    ## input validation
    if not os.path.isfile(geojson_path):
        raise ValueError('geojson_path must be a valid .geojson file.')
    
    if os.path.splitext(os.path.basename(geojson_path))[1] != '.geojson':
        raise ValueError('geojson_path must be a .geojson file.')

    
    if outpath is not None:
        
        if not os.path.isdir(outpath):
            raise ValueError('outpath directory does not exist.')
        
        file_ext = os.path.splitext(os.path.basename(outpath))[1]
        if file_ext not in ['.xlsx','.csv','.shp']:
            raise ValueError('outpath must be .xlsx, .csv, or .shp')
        
        
        ## read geojson and conver to geodataframe
        print('Reading geojson file...')
        gj_df = gpd.read(geojson_path)
        
        ## check if file is empty
        if gj_df.empty:
            raise ValueError('provided geojson file is empty!')
        
        valid_columns = gj_df.column.tolist()
        
        ## check if provided columns are in data file
        not_valid_columns = [c for c in cols if c not in valid_columns]
        if len(not_valid_columns) > 0:
            raise ValueError(f"Invalid columns {not_valid_columns}")
        
        
        ## Write output file
        print('Writing geojson to output file path...')
        
        if file_ext == '.xlsx':
            out_df = gj_df[cols]
            out_df.to_excel(outpath, index=False)
        
        if file_ext == '.csv':
            out_df = gj_df[cols]
            out_df.to_csv(outpath, index=False)
            
        if file_ext == '.shp':
            out_df = gj_df[cols.append('geometry')]
            out_df.to_file(outpath, driver='ESRI Shapefile')

    


    else:
        
        ## read geojson and conver to geodataframe
        print('Reading geojson file...')
        gj_df = gpd.read(geojson_path)
        
        ## check if file is empty
        if gj_df.empty:
            raise ValueError('provided geojson file is empty!')
        
        valid_columns = gj_df.column.tolist()
        
        ## check if provided columns are in data file
        not_valid_columns = [c for c in cols if c not in valid_columns]
        if len(not_valid_columns) > 0:
            raise ValueError(f"Invalid columns {not_valid_columns}")
        
        ## filter df by desired columns
        out_df = gj_df[cols.append('geometry')]


    return out_df