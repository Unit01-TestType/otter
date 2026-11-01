'''
This script contains a function to automatically georeference the png output
from bother back to a tif using the tif output from bother as a template for
georeferencing.
'''

import rasterio as rio
import numpy as np


def georef_png(
    bother_tif,
    bother_png,
    png_scale,
    new_tif,
    crs='epsg:4326',
):
    '''
    Georeference the PNG output from bother using the raster transform from
    the original Bother TIFF.

    The Bother TIFF is treated as the authoritative description of the
    raster grid. This preserves rotated affine transforms.

    Parameters
    ----------
    **bother_tif** : *str, path*
        Path to the original tif output from bother.

    **bother_png** : *str, path*
        Path to the PNG output from bother.

    **png_scale** : *str*
        Expected PNG dimensions in 'widthxheight' format.

    **new_tif** : *str, path*
        File path to new tif to write or overwrite.

    **crs** : *str, optional*
        Coordinate reference system. If the Bother TIFF contains a CRS,
        that CRS is used by default.

    Returns
    -------
    Writes GeoTIFF.
    '''

    # -----------------------------------------------------------------------
    # ROTATION:
    # Read the actual transform from the Bother raster.
    #
    # Do NOT use bother_tif.bounds to reconstruct it. bounds is only the
    # axis-aligned envelope and cannot represent raster rotation.
    # -----------------------------------------------------------------------

    with rio.open(bother_tif) as template:
        transform = template.transform
        template_crs = template.crs
        template_width = template.width
        template_height = template.height

    res = png_scale.split('x')

    if len(res) != 2:
        raise ValueError(
            'png_scale must be in the form "WIDTHxHEIGHT".'
        )

    w = int(res[0])
    h = int(res[1])

    with rio.open(bother_png, 'r') as png:
        d = png.read()

    actual_height = d.shape[1]
    actual_width = d.shape[2]

    # -----------------------------------------------------------------------
    # ROTATION:
    # The transform is valid only if the PNG has exactly the same raster
    # dimensions as the raster for which the transform was created.
    # -----------------------------------------------------------------------

    if actual_width != template_width or actual_height != template_height:
        raise ValueError(
            'The PNG dimensions do not match the dimensions of the '
            'georeferencing template TIFF. '
            f'PNG={actual_width}x{actual_height}, '
            f'TIFF={template_width}x{template_height}. '
            'For rotated maps, the PNG must retain the exact raster '
            'dimensions used to create the TIFF transform.'
        )

    if actual_width != w or actual_height != h:
        raise ValueError(
            'png_scale does not match the actual PNG dimensions. '
            f'png_scale={w}x{h}, '
            f'actual={actual_width}x{actual_height}.'
        )

    d2 = d.astype(np.float32)

    # -----------------------------------------------------------------------
    # Use the TIFF's actual CRS unless the caller explicitly provides one.
    #
    # This maintains the old API while making the template TIFF authoritative
    # for rotated output.
    # -----------------------------------------------------------------------

    output_crs = template_crs if template_crs is not None else crs

    with rio.open(
        new_tif,
        'w',
        driver='GTiff',
        height=d2.shape[1],
        width=d2.shape[2],
        count=1,
        dtype=d2.dtype,
        crs=output_crs,
        nodata=np.nan,
        transform=transform,
    ) as dst:
        dst.write(d2)



# import rasterio as rio
# from rasterio.transform import from_gcps
# from rasterio.control import GroundControlPoint
# import numpy as np


# def georef_png(bother_tif, bother_png, png_scale, new_tif, crs='epsg:4326'):
#     '''
#     Georefenece the png output from bother and convert to tif for editing.
#     The resulting tif can be used used to extract game-grid row,col indices for towns and industry.

#     Parameters
#     ----------
#     **bother_tif** : *str, path*;
#         path to the original tif output from bother.
        
#     **bother_png** : *str, path*;
#         path to the original png output from bother.
        
#     **png_scale** : *str*;
#         scale used to create the png in bother. 'widthxheight'
        
#     **new_tif** : *str, path*;
#         file path to new tif to write or overwrite.
        
#     **crs** : *str, optional*;
#         coordinate reference system by EPSG code. The default is 'epsg:4326'.

#     Returns
#     -------
#     Writes GeoTIFF.

#     '''

#     ras = rio.open(bother_tif)
#     bounds = ras.bounds
#     ras.close()
    
#     res = png_scale.split('x')
#     w = int(res[0]) # width
#     h = int(res[1]) # height

#     # create control points
#     tl = GroundControlPoint(0, 0, bounds[0], bounds[3])
#     tr = GroundControlPoint(0, w, bounds[2], bounds[3])
#     bl = GroundControlPoint(h, 0, bounds[0], bounds[1])
#     br = GroundControlPoint(h, w, bounds[2], bounds[1])

#     gcps = [tl, tr, bl, br]

#     transform = from_gcps(gcps)

#     with rio.open(bother_png, 'r') as png:
#         d = png.read()
#     d2 = d.astype(np.float32)
#     # write to new tif
#     with rio.open(new_tif, 
#                   'w',
#                   driver='GTiff',
#                   height=d2.shape[1],
#                   width=d2.shape[2],
#                   count=1,# numebr of bands
#                   dtype=d2.dtype,
#                   crs=crs,
#                   nodata=np.nan,
#                   transform=transform) as dst:
        
#         dst.write(d2)
        
    