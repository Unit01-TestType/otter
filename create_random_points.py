'''
This script contains functions to facilitate the creation of random
points given special constraints.
Random points can be used to to assign industry locations.

The advantage of these tools is that locations can be contrained to
certain zones meeting defined conditions.

This is an advanced tool requiring knowledge of GIS.

These tools are designed to be used with the georeference png output
from bother.
'''

'''
TODO:
    - refine the default point density based on number of pixels
    - add support for defining zones based on range of row,col bounding boxes
    
    - fix that you have to give method as a dict to have other params be given as dict
    - fix the non-dict route
'''


import os
import rasterio as rio
import rasterio.mask
import geopandas as gpd
import pandas as pd
import numpy as np
import warnings
from tqdm import tqdm
import otter


def create_random_points(ras, zone_shp_path=None, zone_col=None, method=None, 
                         outpath=None, size=None, intensity=None, 
                         center=None, cov=None, n_seeds=2, cluster_radius=None):
    '''
    This function creates random points given zonal and value constraints and returns the
    random lat-long and map row,col index. Use a dict if defining different inputs for 
    multiple zones. If a single value is passed, the input will apply to all zones.

    Parameters
    ----------
    ras : str, path
        path to a raster from georeferenced png output from bother.
    zone_shp_path : str, path, optional
        path to shapefile containing zones. The default is None.
    zone_col : str, optional
        name of the attribute field defining zones. The default is None.
    method : dict
        dictionary defining random points generation methods where the zone id is the key
    outpath : str, path, optional
        path to the output CSV or Excel file or shapefile to write the output dataframe. The default is None.
    size : int, tuple, dict
        number of points to generate; must pass a dict if defining different inputs for multiple zones
    intensity : float, dict
        used for poisson or cluster poisson; must pass a dict if defining different inputs for multiple zones
    center : iter of shape (2,), dict
        a point where simulations will be centered for normal; must pass a dict if defining inputs for multiple zones
    cov : float, array, dict
        std. dev. or 2x2 cov matrix for normal or cluster normal; must pass a dict if defining inputs for multiple zones
    n_seeds : int, dict
        number of sub-clusters to use; must pass a dict if defining inputs for multiple zones
    cluster_radius : float, iter, dict
        radius of each cluster; must pass a dict if defining inputs for multiple zones
    

    Returns
    -------
    DataFrame of random points.

    '''
    
    ''' 
    uniform:
        - https://numpy.org/doc/2.1/reference/random/generated/numpy.random.uniform.html
        - samples uniformly at random
        - size
        
    poisson:
        - https://pysal.org/pointpats/generated/pointpats.random.poisson.html#pointpats.random.poisson
        - intensity, size
        
    normal:
        - https://pysal.org/pointpats/generated/pointpats.random.normal.html#pointpats.random.normal
        - center, cov, size
    
    cluster_poisson:
        - https://pysal.org/pointpats/generated/pointpats.random.cluster_poisson.html#pointpats.random.cluster_poisson
        - intensity, size, n_seeds (sub-clusters), cluster_radius
    
    cluster_normal:
        - https://pysal.org/pointpats/generated/pointpats.random.cluster_normal.html#pointpats.random.cluster_normal
        - cov, size, n_seeds
    
    '''
    
    
    ### load in the shapefile
    shp = gpd.read_file(zone_shp_path)
    
    
    if zone_col is not None:
        
        if zone_col not in shp:
            raise ValueError('zone_col is not a valid field name')
        
        zone_id = list(shp[zone_col].unique())
        
        
        #### If dictionary provided
        if isinstance(method, dict):
            
            zone_points_keys = []
            zone_points_vals = [] # dict of series tied to zone id
            
            ## loop for multiple params given for each zone
            for z in zone_id:
                
                ## subset features by zone
                zone_feat = shp.loc[shp[zone_col] == z]
                
                ## get method
                if z in method:
                    m = method[z]
                else:
                    warnings.warn('Zone id not method key, using uniform by default')
                    m = 'uniform' # default to 'uniform' if key not provided
                
                if m == 'uniform':
                    if size is None:
                        raise ValueError('size needed for uniform distribution')
                    else:
                        s = size[z]
                    
                    ## uniform is default of sample_points
                    zone_sample = zone_feat.sample_points(s) # returns a series
                    
                    zone_points_keys.append(z)
                    zone_points_vals.append(zone_sample.geometry.values[0])
                    
                    
                if m == 'poisson':
                    if size is None:
                        raise ValueError('size needed for uniform distribution')
                    else:
                        s = size[z]
                    
                    if isinstance(intensity, dict):
                        i = intensity.get(z, None)
                    else:
                        i = intensity
                    
                    zone_sample = zone_feat.sample_points(method=m, size=s, intensity=i) # returns a series
                    
                    zone_points_keys.append(z)
                    zone_points_vals.append(zone_sample.geometry.values[0])
                
                
                if m == 'normal':
                    if size is None:
                        raise ValueError('size needed for uniform distribution')
                    else:
                        s = size[z]
                    
                    if isinstance(center, dict):
                        cntr = center.get(z, None)
                    else:
                        cntr = center
                    if isinstance(cov, dict):
                        cv = cov.get(z, None)
                    else:
                        cv = cov
                        
                    zone_sample = zone_feat.sample_points(method=m, size=s, center=cntr, cov=cv) # returns a series
                    
                    zone_points_keys.append(z)
                    zone_points_vals.append(zone_sample.geometry.values[0])
            
            
                if m == 'cluster_poisson':
                    if size is None:
                        raise ValueError('size needed for uniform distribution')
                    else:
                        s = size[z]
                        
                    if isinstance(intensity, dict):
                        i = intensity.get(z, None)
                    else:
                        i = intensity
                    if isinstance(n_seeds, dict):
                        n_s = n_seeds.get(z, 2)
                    else:
                        n_s = n_seeds
                    if isinstance(cluster_radius, dict):
                        c_r = cluster_radius.get(z, None)
                    else:
                        c_r = cluster_radius
                    
                    zone_sample = zone_feat.sample_points(method=m, size=s, intensity=i, n_seeds=n_s, cluster_radius=c_r) # returns a series
                    
                    zone_points_keys.append(z)
                    zone_points_vals.append(zone_sample.geometry.values[0])
                    
            
                if m == 'cluster_normal':
                    if size is None:
                        raise ValueError('size needed for uniform distribution')
                    else:
                        s = size[z]
                    
                    if isinstance(n_seeds, dict):
                        n_s = n_seeds.get(z, 2)
                    else:
                        n_s = n_seeds
                    if isinstance(cov, dict):
                        cv = cov.get(z, None)
                    else:
                        cv = cov
                        
                    zone_sample = zone_feat.sample_points(method=m, size=s, n_seeds=n_s, cov=cv) # returns a series
                    
                    zone_points_keys.append(z)
                    zone_points_vals.append(zone_sample.geometry.values[0])
        
        
        
    
        #### if one method used for all, check for dict for other params
        else:
            
            zone_feat = shp['geometry']
            
            zone_points_keys = shp[zone_col]
            zone_points_vals = []
        
            if method == 'uniform':
                if size is None:
                    raise ValueError('size needed for uniform distribution')
                
                ## uniform is default of sample_points
                zone_sample = zone_feat.sample_points(size) # returns a series
                
                zone_points_vals.append(zone_sample.geometry.values[0])
                
                
            if method == 'poisson':
                if size is None:
                    raise ValueError('size needed for poisson distribution')
                
                if isinstance(intensity, dict):
                    i = intensity.get(z, None)
                else:
                    i = intensity
                
                zone_sample = zone_feat.sample_points(method=method, size=size, intensity=i) # returns a series
                
                zone_points_vals.append(zone_sample.geometry.values[0])
            
            
            if method == 'normal':
                if size is None:
                    raise ValueError('size needed for normal distribution')
                
                if isinstance(center, dict):
                    cntr = center.get(z, None)
                else:
                    cntr = center
                if isinstance(cov, dict):
                    cv = cov.get(z, None)
                else:
                    cv = cov
                    
                zone_sample = zone_feat.sample_points(method=method, size=size, center=cntr, cov=cv) # returns a series
                
                zone_points_vals.append(zone_sample.geometry.values[0])
        
        
            if method == 'cluster_poisson':
                if size is None:
                    raise ValueError('size needed for cluster poisson distribution')
                    
                if isinstance(intensity, dict):
                    i = intensity.get(z, None)
                else:
                    i = intensity
                if isinstance(n_seeds, dict):
                    n_s = n_seeds.get(z, 2)
                else:
                    n_s = n_seeds
                if isinstance(cluster_radius, dict):
                    c_r = cluster_radius.get(z, None)
                else:
                    c_r = cluster_radius
                
                zone_sample = zone_feat.sample_points(method=method, size=size, intensity=i, n_seeds=n_s, cluster_radius=c_r) # returns a series
                
                zone_points_vals.append(zone_sample.geometry.values[0])
                
        
            if method == 'cluster_normal':
                if size is None:
                    raise ValueError('size needed for cluster normal distribution')
                
                if isinstance(n_seeds, dict):
                    n_s = n_seeds.get(z, 2)
                else:
                    n_s = n_seeds
                if isinstance(cov, dict):
                    cv = cov.get(z, None)
                else:
                    cv = cov
                    
                zone_sample = zone_feat.sample_points(method=method, size=size, n_seeds=n_s, cov=cv) # returns a series
                
                zone_points_vals.append(zone_sample.geometry.values[0])
        

    
    #### Merge into a df and extract row,col
    
    shp_pd = pd.DataFrame(shp.drop(columns='geometry'))
    
    d = {zone_col:zone_points_keys,
         'geometry':zone_points_vals}
    zone_points_df = gpd.GeoDataFrame(d)
    zone_points_df = zone_points_df.explode(ignore_index=True) # explode into separate rows for each point
    
    merged_df = shp_pd.merge(zone_points_df,how='inner',on=zone_col)
    merged_df = gpd.GeoDataFrame(merged_df)
    
    zone_rc = otter.get_map_coords(ras=ras,
                                   coords=merged_df)
    
    
    # shapes = zone_points_df.geometry.values.tolist()
    
    # row = [None]*len(shapes)
    # col = [None]*len(shapes)
    
    # with rio.open(ras) as src:
    #     for i in tqdm(range(len(shapes)), position=0, leave=True):
    #         s = [shapes[i]]
    #         out_image, out_transformation = rio.mask.mask(src, s, crop=False) # nodata defaults to 0, this is fine
    #         idx = np.argwhere(out_image)
    #         if not out_image.any():
    #             warnings.warn('Point on water or outside of map. Returning nan')
    #             row[i] = np.nan
    #             col[i] = np.nan
    #         if len(idx) != 0:
    #             # top left corner is 1,1 in OTTD. 
    #             # in GIS, top left corner is 0,0. Need to add 1 to all coordinates
    #             row[i] = idx[0,1] + 1 
    #             col[i] = idx[0,2] + 1
    
    
    # zone_points_df['row'] = row
    # zone_points_df['col'] = col
    
    if outpath is not None:
        print('Writing to file...')
        if os.path.splitext(os.path.basename(outpath))[1] == '.csv':
            zone_rc.to_csv(outpath, index=False)
            
        if os.path.splitext(os.path.basename(outpath))[1] == '.xlsx':
            zone_rc.to_excel(outpath, index=False)
            
        if os.path.splitext(os.path.basename(outpath))[1] == '.shp':
            gdf = gpd.GeoDataFrame(zone_rc, geometry='geometry')
            gdf.crs = 'EPSG:4326'
            gdf.to_file(outpath, driver='ESRI Shapefile')
    
    
    return zone_rc