'''
This script contains the functions that utilize bother to retrieve terrain data
and create a png and tif raster for the heightmap.

bother: https://github.com/bunburya/bother/tree/master

TODO:
    -
'''


'''
bother:
    - bottom left: lat, long
    - top right: lat, long
    
    
Process:
    1. Determine corners of a rectangle for an area of interest
        a. QGIS to make a ratio rectangle or other tools
    2. Run bother for the bounding box with params
        a. create both a png and tif from the SRTM data
    3. Add water, rivers, etc.; edits to tif
    4. Rerun bother using the edited tif to create a new the updated png
        a. if not edited, this is not needed
    5. Convert and georeference png to a tif using the original tif boundaries
    6. Extract row,col indicies for cities and industries using the converted tif
    7. Use the extracted row,col to build code for adding towns and industries in main
    8. Upload the png to OTTD as the heightmap
    
    - bounds: bottom left, top right
    [lat_bl, long_bl, lat_tr, long_tr]
'''




#%% 

'''
This process below can convert the scaled png created from bother and convert it to a tif already
georeferenced and converted back to a tif that will be used to extract row,col indices for towns and industry
'''


import rasterio as rio
from rasterio.transform import from_gcps
from rasterio.control import GroundControlPoint

p = r'C:\Users\marca\OneDrive\Documents\ttnut_test\bother_test_1.tif'
im = r'C:\Users\marca\OneDrive\Documents\ttnut_test\bother_test_1.png'

new_tif = r'C:\Users\marca\OneDrive\Documents\ttnut_test\bother_test_png_to_tif_transform.tif'

ras = rio.open(p)

bounds = ras.bounds # corner bounds of the raster
# tl = [bounds[0],bounds[3]] # long, lat
# tr = [bounds[2],bounds[3]]
# bl = [bounds[0],bounds[1]]
# br = [bounds[2],bounds[1]]

tl = GroundControlPoint(0, 0, bounds[0], bounds[3])
tr = GroundControlPoint(0, 2048, bounds[2], bounds[3])
bl = GroundControlPoint(4096, 0, bounds[0], bounds[1])
br = GroundControlPoint(4096, 2048, bounds[2], bounds[1])

gcps = [tl, tr, bl, br]

transform = from_gcps(gcps)
crs = 'epsg:4326'

with rio.open(im, 'r') as png:
    d = png.read()

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

#%% Testing

# bother(bounds=[29.0001388888888840, -124.8155385698191395, 49.0001388888888840, -114.8155385698191395],
#        outfile = r'D:\Desktop\Programs and Data\openttd\california\bother test\bother_test_1.png',
#        outfile_tif = r'D:\Desktop\Programs and Data\openttd\california\bother test\bother_test_1.tif',
#        epsg='4326',
#        raise_undersea=True,
#        raise_low=True,
#        scale_image = '2048x4096')
