# -*- coding: utf-8 -*-
'''
This script contains a function to automatically georeference the png output from bother
back to a tif using the tif output from bother as a template for georeferencing.
'''

import rasterio as rio
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint


def georef_png(bother_tif, bother_png, png_scale, new_tif, crs='epsg:4326'):
    '''
    Georefenece the png output from bother and convert to tif for editing.
    The resulting tif can be used used to extract row,col indices for towns and industry.

    Parameters
    ----------
    bother_tif : str, path
        path to the original tif output from bother.
    bother_png : str, path
        path to the original png output from bother.
    png_scale : str
        scale used to create the png in bother.
    new_tif : TYPE
        DESCRIPTION.
    crs : TYPE, optional
        DESCRIPTION. The default is '4326'.

    Returns
    -------
    None.

    '''

    ras = rio.open(bother_tif)

    bounds = ras.bounds
    
    res = scale.split('x')
    w = int(res[0]) # width
    h = int(res[1]) # height

    # create control points
    tl = GroundControlPoint(0, 0, bounds[0], bounds[3])
    tr = GroundControlPoint(0, w, bounds[2], bounds[3])
    bl = GroundControlPoint(h, 0, bounds[0], bounds[1])
    br = GroundControlPoint(h, w, bounds[2], bounds[1])

    gcps = [tl, tr, bl, br]

    transform = from_gcps(gcps)

    with rio.open(bother_png, 'r') as png:
        d = png.read()

    # write to new tif
    with rio.open(new_tif, 
                  'w',
                  driver='GTiff',
                  height=d.shape[1],
                  width=d.shape[2],
                  count=1,#numebr of bands
                  dtype=d.dtype,
                  crs=crs,
                  nodata=None, # change if data has nodata value
                  transform=transform) as dst:
        
        dst.write(d)
        
    ras.close()