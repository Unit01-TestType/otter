'''
This script contains functions to facilitate the creation of random
points given special constraints.
Random points can be used to to assign industry locations.

The advantage of these tools is that locations can be contrained to
certain zones meeting defined conditions.

This is an advanced tool requiring knowledge of GIS.

These tools are designed to be used with the georeference png output
from bother.

***Transparency: this function was originally written by Unit01-TestType and revised using ChatGPT.***
'''

'''
TODO:
    - refine the default point density based on number of pixels
    - add support for defining zones based on range of row,col bounding boxes
'''


import os
import warnings
import geopandas as gpd
import pandas as pd
import otter


def create_random_points(ras, zone_shp_path, zone_col, methods=None, outpath=None, **kwargs):
    '''
    Create random points per zone using geopandas.sample_points.

    Parameters
    ----------
    **ras** : *str*;
        Path to a raster for coordinate mapping.
        
    **zone_shp_path** : *str*;
        Path to shapefile containing polygon zones.
        
    **zone_col** : *str*;
        Name of the column defining zone IDs.
        
    **methods** : *dict* or *str*;
        Sampling method per zone (e.g. {"A": "poisson", "B": "normal"}) or a single method for all zones.
        
    **outpath** : *str, optional*;
        Path to save the resulting file (.csv, .xlsx, .shp).
        
    ****kwargs** :
        Keyword arguments that may include:
        - size, intensity, center, cov, n_seeds, cluster_radius, etc.
        Each may be a single value (applies to all zones) or a dict keyed by zone ID.
    

    Returns
    -------
    GeoDataFrame of sampled points with raster coordinates.
    
    
    ## Example Usage
    ```python
    methods = {"zone1": "poisson", "zone2": "normal"}
    kwargs = {
            "size": {"zone1": 100, "zone2": 50},
            "intensity": 0.2,
            "center": {"zone2": [0.5, 0.5]},
            "cov": {"zone2": [[0.1, 0], [0, 0.1]]}
            }
    
    create_random_points("map.tif", "zones.shp", "ZoneID", methods=methods, **kwargs)
    ```

    '''
    
    ''' 
    ## Sampling Methods
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
    
    
   # Load shapefile
    shp = gpd.read_file(zone_shp_path)
    if zone_col not in shp.columns:
        raise ValueError(f"{zone_col} is not a valid field name")

    zone_ids = shp[zone_col].unique()
    results = []

    def get_param(param_name, zone_id):
        """Fetch per-zone parameter, falling back to global value."""
        val = kwargs.get(param_name, None)
        if isinstance(val, dict):
            return val.get(zone_id)
        return val

    for z in zone_ids:
        zone_feat = shp.loc[shp[zone_col] == z]
        method = methods[z] if isinstance(methods, dict) else methods

        # Gather parameters dynamically
        params = {}
        for key in ["size", "intensity", "center", "cov", "n_seeds", "cluster_radius"]:
            val = get_param(key, z)
            if val is not None:
                params[key] = val

        # Default to uniform sampling if no method provided
        if not method:
            warnings.warn(f"No method specified for zone {z}; defaulting to 'uniform'")
            method = "uniform"

        # Validate minimum required parameters
        if "size" not in params:
            raise ValueError(f"Parameter 'size' required for zone {z} ({method})")

        # sample_points call, unpacking dynamic parameters
        zone_sample = zone_feat.sample_points(method=method, **params)

        temp = pd.DataFrame({
            zone_col: [z] * len(zone_sample),
            "geometry": zone_sample.geometry.values[0]
        })
        results.append(temp)

    # Merge and explode
    zone_points_df = gpd.GeoDataFrame(pd.concat(results, ignore_index=True))
    merged_df = shp.drop(columns="geometry").merge(zone_points_df, on=zone_col)
    merged_df = gpd.GeoDataFrame(merged_df, geometry="geometry")

    # Map to raster coords
    zone_rc = otter.get_map_coords(ras=ras, coords=merged_df)

    # Output
    if outpath:
        ext = os.path.splitext(outpath)[1].lower()
        print(f"Writing to {outpath}...")
        if ext == ".csv":
            zone_rc.to_csv(outpath, index=False)
        elif ext == ".xlsx":
            zone_rc.to_excel(outpath, index=False)
        elif ext == ".shp":
            gdf = gpd.GeoDataFrame(zone_rc, geometry="geometry", crs="EPSG:4326")
            gdf.to_file(outpath)
        else:
            warnings.warn(f"Unrecognized output extension '{ext}', skipping write.")

    return zone_rc