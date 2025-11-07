'''
This script contains an adaptation of bother by bunburya for to work with otter to retrieve terrain data
and create a png and tif raster for the heightmap.

bother: https://github.com/bunburya/bother/tree/master

TODO:
    - allow bounds to be read from shapefile directly
'''


import sys
import logging
import math
import time
import os
import os.path
import tempfile
from typing import Optional, Set, Tuple, List

from PIL import Image
from rasterio.io import MemoryFile

from otter.bother_utils.srtm import create_tif_file, clear_cache
from otter.bother_utils.heightmap import (remove_sea, resample, reproject_raster, set_lakes_to_elev, raise_undersea_land,
                                    raise_low_pixels, to_png, crop_modes, crop_image, scale_image_f, png_to_file)

# EPSG codes
WGS84 = 4326  # Mercator - The default CRS used in the STRM data
PSEUDO_MERCATOR = 3857  # Web Mercator - The projection used by Google Maps, OpenStreetMap, etc.

def error(msg: str):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)

def bother(outfile, bounds=None, outfile_tif=None, infile_tif=None, scale_data=None, epsg='4326', raise_low=0, 
           raise_undersea=None, no_sea=None, lakes=None, max_brightness=255, infile_png=None, crop=None,
           scale_image=None):
    '''
    Run bother to download SRTM elevation data.

    Parameters
    ----------
    **bounds** : *list*;
        Bounding box; bottom left and top right in lat long.
        
    **outfile** : *str, path*;
        The file to which the greyscale PNG image will be written.
        
    **outfile_tif** : *str, path*
        Path to output tif file.
        
    **infile_tif** : *str, path, optional*;
        Path to a tif file containing elevation data. The default is None.
        
    **scale_data** : *float, optional*;
        more than 1 will upsample the data resolution; less than 1 downsample the data resolution. The default is None.
        
    **epsg** : *int, optional*;
        Coordinate Reference System EPSG code to project data. The default is '4326'.
        
    **raise_low** : *float, optional*;
        Values below the input will be rounded down to 0. The default is 0.
        
    **raise_undersea** : *int, optional*;
        Raise pixels with an elevation below zero (ie, land that is below sea-level) to the given level. The default is None.
        
    **no_sea** : *float, optional*;
        Raise pixels with low elevation so that they have a non-zero value in the resulting greyscale image. Only values with elevations above the above that value will be raised.
        
    **lakes** : *int, optional*;
        Detect lakes and set to 0; provided value is the minimum number of contiguous pixels needed. The default is None.
        
    **max_brightness** : *int, optional*;
        Set the highest point of the elevation to the provided value rather than 255. The default is None.
        
    **infile_png** : *str, path, optional*;
        Path to output png file. The default is None.
        
    **crop** : *str, optional*;
        Crop the resulting image to WIDTH x HEIGHT. MODE determines which region of the image to crop to and must be one of nw, n, ne, e, c, w, sw, s, se. The default is None.
        
    **scale_image** : *str, optional*;
        Scale the resulting image to WIDTH x HEIGHT. The default is None.

    Returns
    -------
    Writes GeoTIFF and/or PNG.

    '''
    
    
    '''
    Check inputs - adapted from check_namespace
    '''
    
    if (bounds is None) and (infile_tif is None) and (infile_png is None):
        error('Must pass bounds, infile_tif or infile_png.')
    elif sum(((bounds is not None), (infile_tif is not None), (infile_png is not None))) > 1:
        error('bounds, infile_tif and infile_png are mutually exclusive.')
    
    if bounds is not None:
        if len(bounds) != 4:
            error('bounds must be a list of 4 values.')
    
    if (scale_data is not None) and scale_data == 0:
        error('0 is invalid value for scaling.')
        
    
    if crop:
        res, mode = crop
        if mode.lower() not in crop_modes:
            error(f'Mode must be one of {crop_modes}.')
        res = res.split('x')
        try:
            width = int(res[0])
            height = int(res[1])
        except (IndexError, ValueError):
            error('Size for cropped image must be in form "WIDTHxHEIGHT", where WIDTH and HEIGHT are integers.')
        if (width <= 0) or (height <= 0):
            error(f'Invalid dimensions for cropping: {width}x{height}.')
            
        
    if scale_image:
        res = scale_image.split('x')
        try:
            width = int(res[0])
            height = int(res[1])
        except (IndexError, ValueError):
            error('Size for scaled image must be in form "WIDTHxHEIGHT", where WIDTH and HEIGHT are integers.')
    
        if (width <= 0) or (height <= 0):
            error(f'Invalid dimensions for scaling: {width}x{height}.')
            
    
    '''
    Set defaults if params given as boolean
    '''
    if lakes == True:
        lakes = 80
    if raise_undersea == True:
        raise_undersea == 1
    if raise_low == True:
        raise_low = 0.0
    
    
    '''
    Parse arguments - adapted from parse_namespace
    '''
    tmp_file = None
    
    ## if bouding box is provided, create a tif from SRTM data
    if bounds:
        if outfile_tif:
            to_file = os.path.abspath(outfile_tif)
        else:
            to_file = os.path.join(tempfile.gettempdir(), f'othg_{time.time()}.tif')
            tmp_file = to_file
        lat1, lon1, lat2, lon2 = bounds
        tif_file = create_tif_file(lon1, lat1, lon2, lat2, to_file)
    ## else if bounds is None, use existing infile_tif file
    else:
        tif_file = infile_tif

    if tif_file:
        with open(tif_file, 'rb') as f:
            #memfile = handle_nodata(MemoryFile(f))
            memfile = MemoryFile(f)
            if scale_data is not None:
                memfile = resample(memfile, scale_data)
            if no_sea:
                memfile = remove_sea(memfile)
            if epsg and (epsg != WGS84):  # The SRTM data already uses WGS84 so no need to reproject to that 
                memfile = reproject_raster(memfile, dst_crs=f'EPSG:{epsg}')
            if lakes:
                memfile = set_lakes_to_elev(memfile, lakes)
            if raise_undersea is not None:
                memfile = raise_undersea_land(memfile, raise_undersea)
            if raise_low is not None:
                print(type(max_brightness))
                memfile = raise_low_pixels(memfile, raise_low, max_brightness)
            im = to_png(memfile, not raise_low, max_brightness)
    elif infile_png:
        im = Image.open(infile_png)
        
    if crop:
        res, mode = crop
        res = res.split('x')
        width = int(res[0])
        height = int(res[1])
        im = crop_image(im, width, height, mode)
    if scale_image:
        res = scale_image.split('x')
        width = int(res[0])
        height = int(res[1])
        im = scale_image_f(im, width, height)
        
    if outfile.endswith('.png'):
        save_to = outfile
    else:
        save_to = outfile + '.png'
        
    try:
        png_to_file(im, save_to)
    except FileNotFoundError:
        error(f'Could not save to {save_to}.  Check that the directory to which you want to save exists.')
    
    if tmp_file:
        os.remove(tmp_file)
    if clear_cache:
        clear_cache()