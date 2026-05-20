'''
This script contains a function to utilize GeoNames to retrieve a list of cities within a bounding box.

The bounding box must be provided as a list of latitude and longitude like [north, south, east, west] 
or a shapefile or a geodataframe.

NOTE: The GeoNames API limits users to a maximum of 10000 credits per day and 1000 credits per hour.

Direct JSON return from GeoNames is formatted with these fields:
    
    lng: longitude
    geonameId: unique ID from GeoNames
    countrycode: ISO A2 country code (https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes)
    name: city name
    fclName: feature class name
    toponymName: toponym name
    fcodeName: feature code name
    wikipedia: link to wikipedia page
    lat: latitude
    fcl: feature class
    population: city population
    fcode: feature code (https://www.geonames.org/export/codes.html)


    Feature Classes --
    A: adminsitrative feature: country, state, region, ...
    H: hydrographic features: stream, lake, ...
    L: area features: parks, area, ...
    P: populated places features: city, village, ...
    R: road/railroad features: road, railroad
    S: spot features: spot, building, farm
    T: hypsographic features: mountain, hill, rock, ...
    U: undersea features
    V: vegetation features: forest, heath, ...


'''

'''
TODO:
    - add paging to allow more than 1000 results
    - reorganize data columns before writing to file
    - reorganize bounds order to match bother input
    - handle error messages
    
'''

import os
import requests
import json
import pandas as pd
import geopandas as gpd

import osmnx as ox

def find_cities(bounds, geonames_username, language='en', max_cities=100,
                outdir=None, fileformat='csv', filename='cities', shp=False):
    '''
    This function sends a request to the GeoNames API and returns cities within a bounding box.
    NOTE: A GeoNames account is required. Make a free account and enable for free webservices: https://www.geonames.org/login

    Parameters
    ----------
    **bounds** : list, GeoDataFrame, str, path;
        Bounding box as a lat-long list of [north, south, east, west] or a geodataframe or a path to a shapefile.
        
    **geonames_username** : *str*;
        GeoNames account username. The account must be activated for webserves.
        
    **language** : *str, optional*;
        ISO language code for city names. The default is 'en'. https://www.loc.gov/standards/iso639-2/php/English_list.php
        
    **max_cities** : *str*, int, optional;
        Maximum number of cities to return. Cities are prioritized by population and capitals. The maximum is 1000. The default is 100.
        
    **outdir** : *str, path, optional*;
        Output directory. If provided, output files will be written to fileformat. The default is None.
        
    **fileformat** : *str, optional*;
        File format to write to outdir. Format must be shp, csv, xlsx, or json The default is csv.
        
    **filename** : *str, path, optional*;
        Name of the output file. The default is cities.
        
    **shp** : *boolean, optional*;
        Flag to write a shapefile of the output. This can be used without fileformat. The default is False.
        

    Returns
    -------
    GeoPandas Dataframe of cities.

    '''
    
    
    #### Bounds format check
    ## check if list
    if isinstance(bounds, list):
        if len(bounds) != 4:
            raise ValueError('bounds must be a list of [north, south, east, west].')
    
    ## check if geodataframe
    elif isinstance(bounds, gpd.GeoDataFrame):
        if bounds.crs != "EPSG:4326":
            raise ValueError('Input GeoDataframe must use CRS EPSG 4326.')
        if len(bounds) > 1:
            raise ValueError('Only 1 boundary feature can be processed at a time. '+str(len(bounds))+' features provided.')
        bounds = [bounds['minx'][0], bounds['miny'][0], bounds['maxx'][0], bounds['maxy'][0]]

    ## check if shapefile
    elif isinstance(bounds, str):
        ext = os.path.splitext(os.path.basename(bounds))[1]
        if ext != '.shp':
            raise ValueError('Input file path must be a shapefile.')
        bounds = gpd.read_file(bounds)
        if bounds.crs != "EPSG:4326":
            raise ValueError('Input GeoDataframe must use CRS EPSG 4326.')
        if len(bounds) > 1:
            raise ValueError('Only 1 boundary feature can be processed at a time. '+str(len(bounds))+' features provided.')
        bounds = [bounds['minx'][0], bounds['miny'][0], bounds['maxx'][0], bounds['maxy'][0]]
    
    
    ## check max_cities input
    try:
        max_cities = str(max_cities)
        if not isinstance(int(max_cities), int):
            raise ValueError("max_cities must be an integer")
        ## add paging to increase limit...
        # if int(max_cities) > 1000:
        #     raise ValueError("max_cities must not exceed 1000")
    except:
        raise ValueError("max_cities must be an integer")
    
    

    ox.config(use_cache=True, log_console=True)    

    # Construct the bounding box string for the geocoding service
    # bbox = [28.9539681097028065, 129.1673112741469254, 45.6434786208784402, 145.8568217853225235] # bottom, left, top, right
    bbox = [129.1673112741469254, 28.9539681097028065, 145.8568217853225235, 45.6434786208784402] # left, bottom, right, top
    # bbox = [45.6434786208784402, 28.9539681097028065, 129.1673112741469254, 145.8568217853225235] # north, south, east, west
    tags = {"place":"city", "place":"town", "place":"village"}
    gdf = ox.features.features_from_bbox(bbox=bbox, tags=tags)
    
    ## base URL for a cities query
    # api_cities_url = "http://api.geonames.org/citiesJSON"
    
    # ## combine params
    # params = {"north": bounds[0],
    #           "south": bounds[1],
    #           "east": bounds[2],
    #           "west": bounds[3],
    #           "lang": language,
    #           "maxRows": max_cities,
    #           "username": geonames_username}
    
    
    
    #### Send request to GeoNames
    # response = requests.get(api_cities_url, params=params)
    # response.raise_for_status() # raise HTTP error if unsuccessful
    # json_dict = response.json()
    
    # ## convert json to dataframe
    # cities_df = pd.DataFrame.from_dict(json_dict['geonames'])
    
    # ## convert to geodataframe from longitude and latitude
    # cities_gdf = gpd.GeoDataFrame(cities_df, 
    #                              geometry=gpd.points_from_xy(cities_df['lng'], cities_df['lat']), 
    #                              crs="EPSG:4326")
    
    
    #### Write to file
    if outdir is not None:
        if not os.path.isdir(outdir):
            raise ValueError("outdir must be a valid directory")
        
        ## write to csv
        if fileformat == 'csv':
            outpath = os.path.join(outdir, filename+'.csv')
            cities_df.to_csv(outpath, index=False)
        
        ## write to xlsx
        if fileformat == 'xlsx':
            outpath = os.path.join(outdir, filename+'.xlsx')
            cities_df.to_excel(outpath, index=False)
        
        ## write to json (original format)
        if fileformat == 'json':
            outpath = os.path.join(outdir, filename+'.json')
            with open(outpath, "w") as f:
                json.dump(response.json(), f, indent=4)  # `indent=4` for pretty-printing
    
        ## write to shapefile
        if shp:
            outpath = os.path.join(outdir, filename+'.shp')
            cities_gdf.to_file(outpath, driver='ESRI Shapefile')
    
    
    
    
    return cities_gdf