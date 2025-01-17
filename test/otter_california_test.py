'''
This script tests the otter package using a scenario built on the North American west coast.
This script also lays out an example workflow for using otter.
'''

import otter


#### Run bother to download elevation data
# the initial output tif will be the original resolution
# this only needed to grab the bounds to georeference the png; it can be overwritten later
bother_tif = r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3.tif'
png_path = r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3.png'
png_scale = '2048x4096'

otter.bother(bounds=[29.0001388888888840, -124.8155385698191395, 49.0001388888888840, -114.8155385698191395],
             outfile=png_path,
             outfile_tif=bother_tif,
             epsg='4326',
             raise_undersea=True,
             raise_low=True,
             scale_image=png_scale)

#### Georeference png to a tif for editting and row,col extaction
otter.georef_png(bother_tif=bother_tif, # overwrite original tif to georeferenced png 
                 bother_png=png_path, 
                 png_scale=png_scale, 
                 new_tif=bother_tif)


#### Edit terrain to add land or water
## Add land
# otter.add_land(ras,
#                shp_path,
#                outpath,
#                elevation)

#%% 
### Add water

otter.add_water(ras=bother_tif,
                shp_path=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\water\US_rivers_all.shp',
                # outpath=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3_water.tif',
                outpath=bother_tif,
                select_col='river',
                select_val='Yes',
                buffer=1)

## Clear area around Lewiston, ID
otter.add_water(ras=bother_tif,
                shp_path=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\water\lewiston_water.shp',
                outpath=bother_tif)

otter.add_land(ras=bother_tif,
               shp_path=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\water\lewiston_elev_1.shp',
               outpath=bother_tif,
               elevation=1)

## Add water near portland for port
otter.add_water(ras=bother_tif,
                shp_path=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\water\portland_water.shp',
                outpath=bother_tif)


## Rerun bother to convert tif to png
otter.bother(infile_tif=bother_tif,
             outfile=png_path)



#### Build gamescript code
## Get towns locations
town_tiles = otter.get_map_coords(ras=bother_tif,
                                  coords=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3_towns.xlsx',
                                  lat_col='Lat',
                                  long_col='Long',
                                  select_col='map',
                                  select_val='yes')

## Get industry locations
industry_tiles = otter.get_map_coords(ras=bother_tif,
                                      coords=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3_industry_NAIS.xlsx',
                                      lat_col='Lat',
                                      long_col='Long')

## Generate random points within zones
# method_dict = {'10':'uniform',
#                '45':'uniform'}
# size_dict = {'10':5,
#              '45':10}
# industry_tiles_zones = otter.create_random_points(ras=bother_tif,
#                                                   zone_shp_path=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\zones\industry.shp',
#                                                   zone_col='ind_code',
#                                                   method=method_dict,
#                                                   size=size_dict)

#%% 
## Get canal locations
canal_tiles = otter.get_map_coords(ras=bother_tif,
                                   coords=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\GIS\water\inland_water.shp',
                                   select_col='map',
                                   select_val='Yes')

## Get sign locations
sign_tiles = otter.get_map_coords(ras=bother_tif,
                                  coords=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\Signs_CA3.xlsx',
                                  lat_col='prim_lat_dec',
                                  long_col='prim_long_dec',
                                  select_col='map',
                                  select_val='yes')

#%% 
## build info
otter.build_info(outdir=r'C:\Users\Marc\Documents\OpenTTD\game\CA-townplacer3',
                 author='Unit01-TestType',
                 name='CA-townplacer3',
                 short_name='CATP',
                 description='A gamescript for a real-world West Coast scenario',
                 version='SELF_VERSION',
                 date='2024-12-16',
                 API_version='1.11',
                 url='',
                 comment='')

## build version
otter.build_version(outdir=r'C:\Users\Marc\Documents\OpenTTD\game\CA-townplacer3',
                    version='3')

#%% 
## build main
## towns code
# towns_code = otter.build_towns_code(towns=town_tiles,
#                                     town_x_header='row',
#                                     town_y_header='column',
#                                     town_size_header='town type',
#                                     city_header='city',
#                                     town_name_header='Name',
#                                     town_pop_header='OTTD pop')

towns_code = otter.build_towns_code(towns=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3_towns.xlsx',
                                    town_x_header='row',
                                    town_y_header='column',
                                    town_size_header='town type',
                                    city_header='city',
                                    town_name_header='Name',
                                    town_pop_header='OTTD pop')

## industry code
# industry_code = otter.build_industry_code(industry=industry_tiles,
#                                           ind_x_header='row',
#                                           ind_y_header='col',
#                                           ind_name_header='Name',
#                                           ind_type_header='ind code',
#                                           trylevel_header='trylevel',
#                                           level_x2_header='level_x2',
#                                           level_y2_header='level_y2'
#                                           )

industry_code = otter.build_industry_code(industry=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\california_3_industry_NAIS.xlsx',
                                          ind_x_header='row',
                                          ind_y_header='col',
                                          ind_name_header='Name',
                                          ind_type_header='ind code',
                                          trylevel_header='trylevel',
                                          level_x2_header='level_x2',
                                          level_y2_header='level_y2'
                                          )

## canals code
canals_code = otter.build_canal_code(canals=canal_tiles,
                                     x_header='row',
                                     y_header='col')


## signs code
signs_code = otter.build_signs_code(signs=r'D:\Desktop\Programs and Data\openttd\california\California-3.0\Signs_CA3.xlsx',
                                    x_header='row',
                                    y_header='column',
                                    label_header='feature_name')


## build main file
otter.build_main(outdir=r'C:\Users\Marc\Documents\OpenTTD\game\CA-townplacer3',
                 towns_code=towns_code,
                 industry_code=industry_code,
                 canal_code=canals_code,
                 signs_code=signs_code
                 )


#### Load gamescript into OpenTTD scenario builder
#### Save sceanrio after building from gamescript



