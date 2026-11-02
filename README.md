<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->


<!-- PROJECT LOGO -->


# **otter** -- **O**pen**TT**d map mak**ER** tools

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#motivation">Motivation</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#windows-installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#additional-features">Additional Features</a></li>
    <li><a href="#known-issues">Known Issues</a></li>
    <li><a href="#future">Future</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->

## About the Project
**OTTER HAS NOT BEEN TESTED FOR OTTD 15.X**

Otter provides tools to help create real-world custom maps and scenarios in OpenTTD.
Otter takes a GIS approach to custom map-making in OpenTTD and offers workflows to 
help SAVE scenario information outside of OpenTTD for revision and replication.
GIS knowledge is not required to use the tools in otter, but having a firm grasp of 
GIS concepts and software will help to unlock the full potential of otter in your map-making workflows. 
Much of otter revolves around data transformations of real-world coordinates into game-grid coordinates
and vice versa.

Otter utilizes [Bother by Bunburya](https://github.com/bunburya/bother) to provide a pure pythonic method of downloading
SRTM terrain data and scaling images to quickly develop heightmaps

Otter can be used to:
- Create heightmaps with Bother
- Create GIS compatible georeferenced rasters of Bother heightmap images
- Edit heightmap elevations using GIS data
- Query OSM to gather locations and populations of real-world cities and towns
- Convert real-world locations of cities and towns from common data formats (e.g. Excel, CSV) 
into game-grid coordinates compatible with the new JSON import tool
- Convert other features from real-world coordinates or shapefiles into game-grid coordinates
- Create a gamescript to import towns, industries, signs, and "high elevation water" (e.g. mountain lakes)


**NOTE:**
Otter is far from complete. I have much more experience with python and GIS than I do gamescript development and C++/Squirrel. 
The gamescript code component of otter is by far the weakest part, but it works well enough to get the job done for now.
I would greatly appreciate feedback and contributions to the gamescript code to improve functionality. 


### Motivation

Otter was concieved after countless hours of searching old forum posts for information
about creating custom maps for OpenTTD. Unfortunately, I found that many of the methods and tools were 
overly cumbersom, outdated, or simply no longer available.

This project was inspired by ideas and concepts from previous attempts at custom map and terrain generation:

https://www.tt-forums.net/viewtopic.php?t=69007

https://www.tt-forums.net/viewtopic.php?f=29&t=70846

https://www.tt-forums.net/viewtopic.php?t=68926

https://www.tt-forums.net/viewtopic.php?f=65&t=67181

https://reddit.com/r/openttd/comments/gkw45v/any_tips_for_finding_where_real_world_towns/

https://github.com/internet-trains/terrain

https://tangrams.github.io/heightmapper/

https://github.com/bunburya/bother

It became increasing apparent that much of the discussion of newGRF and custom scenario development
takes place on the OpenTTD Discord server and is not easily indexed for research. For this reason,
I wanted to make otter as accessible as possible for the OpenTTD community and provide this repository as a place
to compile additional resources for custom map and scenario development to avoid "reinventing the wheel".


## Recent Custom Map-Making Tool Developments

### OpenTTD Heightmap Generator
Zyliety recently released a web-based GUI that uses Bother to create heightmaps. The GUI also queries
OSM data to gather cities and towns within the bounding box to import as json into OTTD.

https://github.com/zyliety/OpenTTD-Heightmap-Generator 


<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

Otter requires the following python packages:
* rasterio
* shapely
* fiona
* geopandas
* pandas
* numpy
* pointpats
* tqdm
* pillow
* scipy
* pyproj

If you are using the Anaconda package manager for Windows, these packages should be installed 
using conda forge when possible. If you're totally new to python, [here is a beginner's guide to using Anaconda in Windows](https://www.anaconda.com/blog/anaconda-python-complete-beginners-guide)

### Windows Installation

1. Clone the repo OR simply download a zip by clicking the green "Code" dropdown in the upper right.
   ```sh
   git clone https://github.com/Unit01-TestType/otter.git
   ```
2. Place the repo into your python packages
If you're using Anaconda, unzip the folder and place the entire otter folder
into the site-packages folder in your Anaconda python environment which should be a
path that look something like this

   ```sh
   C:\Users\name\anaconda3\envs\env1\Lib\site-packages
   ```
3. Import otter to your python script

   ```python
   import otter
   ```


### Town Data Resources

#### otter.query_places

otter.query_places()
Otter includes a built-in interface to the OpenStreetMap Overpass API. query_places() 
retrieves point locations for cities, towns, villages, and hamlets within a specified geographic bounding box.

The function returns a pandas DataFrame. You can also optionally save the results to a file by providing an output path. 
Supported output formats include CSV, Excel, GeoJSON, and Shapefile.

```python


# Bounding box:
# (latitude south, longitude west,
#  latitude north, longitude east)
west_coast_bbox = (
    29.0001388888888840,
    -124.8155385698191395,
    49.0001388888888840,
    -114.8155385698191395,
)

# Retrieve cities and towns, requesting English names where available.
places = otter.query_places(
    bbox=west_coast_bbox,
    place_types=("city", "town"),
    name_languages=("en",),
    output="west_coast_places.xlsx",
)

# The function also returns the results as a DataFrame.
print(places.head())
```

Selecting place types

The place_types argument determines which OSM place classifications are included. The available types are:
- city
- town
- village
- hamlet
For example, to include smaller settlements:

```python
places = otter.query_places(
    bbox=west_coast_bbox,
    place_types=("city", "town", "village", "hamlet"),
)
```

Selecting name languages

The name_languages argument allows users to request names in one or more languages. For example:

```python
places = otter.query_places(
    bbox=west_coast_bbox,
    place_types=("city", "town"),
    name_languages=("en", "es", "fr"),
)
```

When a requested language is unavailable for a place, the function reports the missing language and available alternatives. 
It can still return other requested language columns where those names exist. The original/local name should remain available as well.

Custom queries and advanced options

Users can provide a custom Overpass query when the built-in place query does not meet their needs. 
Other options allow control over administrative information, API servers, request timeouts, retries, caching, and subdivision of large geographic requests.

For a complete list of options and their defaults, see the query_places() function documentation.




#### Alternative: Custom Overpass Turbo Queries

Real-world city and town data can be aquired in many different ways. One method that includes a GUI interface 
is to use [Overpass Turbo](https://overpass-turbo.eu/) to query all cities and towns within a bounding
box and export the coordinates and population data as a geojson file. You can use the same coordinate
bounding box used to generate the heightmap.

Example Overpass Turbo query:
```c
[out:json][timeout:300];
// gather results
(
  node["place"="city"]({{bbox}});
  node["place"="town"]({{bbox}});
);
// print results
out geom;
```

{{bbox}} will use the visual map by default. But you can repalce {{bbox}} with exact 
latitude and longitude coordinates to specifiy a precise bounding box.


Example bounding box for the US West Coast Example:

```c
[out:json][timeout:300];
// gather results
(
  node["place"="city"](29.0001388888888840, -124.8155385698191395, 49.0001388888888840, -114.8155385698191395);
  node["place"="town"](29.0001388888888840, -124.8155385698191395, 49.0001388888888840, -114.8155385698191395);
);
// print results
out geom;
```

Export the query results to GeoJson and convert the GeoJson file using:

```python
otter.convert_geojson(geojason_path, # path to a geojson file
                outpath=None, # optional, output file path for Excel, CSV, or shapefile. File type inferred from file exension.
                cols=['name','population','longitude','latitude'], # optional, a list of columns to keep from the raw geojson
# returns a geopandas GeoDataFrame. If outpath is not None, a file is also written.
```


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage
### US West Coast Example
The files for this example can be found in "Examples"

This example requires the North American Industry Replacement Set (NAIS) newGRF.

1. Use Bother to download the SRTM terrain data for a bounding box that covers the 
US West Coast.
```python
## import the otter package
import otter

## define the output raster tif output file path
## this is needed to get the georeference information
bother_tif = 'california.tif'

## define the output image path
png_path = 'california.png'

## define the intended map-grid scale
## Bother will scale the downloaded data to have these pixel dimensions
## [width]x[height]
png_scale = '2048x4096'

## define the bounding box of the game grid
## the format is: latitude bottom left, longitude bottom left, latitude top right, longitude top right
## Note: corners refer to the corners of the intended game grid
corners = [
            (49.0001388888888840, -124.8155385698191395),  # top-left
            (49.0001388888888840, -114.8155385698191395),  # top-right
            (29.0001388888888840, -114.8155385698191395),  # bottom-right
            (29.0001388888888840, -124.8155385698191395),  # bottom-left
          ]
otter.bother(corners=corners,
             outfile=png_path,
             outfile_tif=bother_tif,
             epsg='4326',
             raise_undersea=True,
             raise_low=True,
             scale_image=png_scale)
```
    
2. Convert the scaled PNG to a georeferenced GeoTIFF file.

```python
otter.georef_png(bother_tif=bother_tif, # overwrite original tif to with scaled png  
                 bother_png=png_path, 
                 png_scale=png_scale, 
                 new_tif=bother_tif)
```

3. Add rivers and low-land water

```python
## Modify the GeoTIFF heightmap to add water by setting the
## pixel values to 0 (sea level) where the shapefile features overlap
otter.add_water(ras=bother_tif,
                shp_path='US_rivers_all.shp', # shapefile with river features
                outpath=bother_tif, # overwrite the existing raster heightmap
                # filter the features in the shapefile (optional)
                # to only look at features with a value of 'Yes' in the 'river' column
                select_col='river', 
                select_val='Yes',
                buffer=1) # select a minimum of 1 tile where the shapefile intersects
                
                
## Expand the water area around Lewiston, ID to give space to add a bulk terminal
otter.add_water(ras=bother_tif,
                shp_path='lewiston_water.shp',
                outpath=bother_tif)

## Flaten some land around Lewiston, ID to give space to add a bulk terminal
otter.add_land(ras=bother_tif,
               shp_path='lewiston_elev_1.shp',
               outpath=bother_tif,
               elevation=1)
```

4. After modifying the GeoTIFF heightmap, convert back to a PNG

```python
## Bother can be used to scale or convert existing GeoTIFF files
otter.bother(infile_tif=bother_tif,
             outfile=png_path)
```
    
    

5. Get the game-grid coordinates of the towns from real-world coordinates

Note: The town locations for this example are supplied in california_towns.xlsx. 
This file contains a curated selection of towns for the example scenario. 
It is intentionally used instead of querying OpenStreetMap at runtime so that the 
example remains reproducible and produces the intended town placement. 
Users who want to generate their own town dataset can use otter.query_places() as described in the Town Data Resources section.

```python
## convert real-world coordinates of towns from 
## an excel file containing the latitude and longitudes,
town_tiles = otter.get_map_coords(ras=bother_tif,
                                  coords='california_towns.xlsx',
                                  lat_col='Lat', # name of the column containing latitude
                                  long_col='Long', # name of the column containing longitude
                                  select_col='map', # name of filter column
                                  select_val='yes') # value to filter rows
## the output is a dataframe variable of the original excel file
## with columns for row and column index pairs for the game-grid
```
    
6. Get the game-grid coordinates of industries from real-world coordinates

```python
## convert real-world coordinates of industries
## from an excel file containing latitude and longitudes
industry_tiles = otter.get_map_coords(ras=bother_tif,
                                      coords='california_industry_NAIS.xlsx',
                                      lat_col='Lat',
                                      long_col='Long')
## the output is a dataframe variable of the original excel file
## with columns for row and column index pairs for the game-grid
```
    
7. Get game-grid coordinates of high-elevation water which will be placed as canals

```python
## Get high-elevation water locations from a shapefile
## which will be placed as canals
## every tile underlaying the shapefile will be returned
canal_tiles = otter.get_map_coords(ras=bother_tif,
                                   coords='inland_water.shp', # shapefile defining the water area
                                   select_col='map',
                                   select_val='Yes')
```
    
8. Get game-grid coordinates for signs

```python
## Get sign locations
sign_tiles = otter.get_map_coords(ras=bother_tif,
                                  coords='Signs_CA3.xlsx',
                                  lat_col='prim_lat_dec',
                                  long_col='prim_long_dec',
                                  select_col='map',
                                  select_val='yes')
```



9. Start building the gamescript files

```python
## place to build the gamescript files
## replace this with the appropriate path on your computer
outdir = r'C:\Users\[name]\Documents\OpenTTD\game\CA-townplacer3'

## build info file
otter.build_info(outdir=outdir,
                 author='Unit01-TestType',
                 name='CA-townplacer3',
                 short_name='CATP',
                 description='A gamescript for a real-world West Coast scenario',
                 version='SELF_VERSION',
                 date='2024-12-16',
                 API_version='14',
                 url='',
                 comment='')

## build version file
otter.build_version(outdir=outdir,
                    version='3')
```

10. Generate the gamescript code lines to add towns, industries, canals, and signs

```python
## generate the code lines to add towns that will be added to main.nut
towns_code = otter.build_towns_code(towns=town_tiles,
                                    town_x_header='row',
                                    town_y_header='column',
                                    town_size_header='town type',
                                    city_header='city',
                                    town_name_header='Name',
                                    town_pop_header='OTTD pop')
                                    
                              
## code lines to add industries      
industry_code = otter.build_industry_code(industry=industry_tiles,
                                          ind_x_header='row',
                                          ind_y_header='col',
                                          ind_name_header='Name',
                                          
                                          # column name of the reference type code for the industry
                                          # NAIS industry type codes can be found in the documentation
                                          ind_type_header='ind code',
                                          
                                          # industries require level land to be placed
                                          # trylevel is a flag for whether to level the land if there is 
                                          # and error trying to place the industry
                                          trylevel_header='trylevel',
                                          
                                          # these columns give the minimum x and y dimensions of the area to level
                                          level_x2_header='level_x2',
                                          level_y2_header='level_y2')
                                          
## code lines to add high-elevation water as canals
canals_code = otter.build_canal_code(canals=canal_tiles,
                                     x_header='row',
                                     y_header='col')

## code lines to add signs
signs_code = otter.build_signs_code(signs=sign_tiles,
                                    x_header='row',
                                    y_header='column',
                                    label_header='feature_name')
```

11. Build the main.nut file for the gamescript
    
```python
## create the main.nut file with the other code lines to add
## towns, industries, canals, and signs
otter.build_main(outdir=outdir,
                 towns_code=towns_code,
                 industry_code=industry_code,
                 canal_code=canals_code,
                 signs_code=signs_code)
```

12. Open the Scenario Editor and load the heightmap PNG. Open the Gamescript settings
and select the newly created gamescript. If the gamescript is not in the list, there may be an
error with the code somewhere (close and reopen OTTD if the gamescript was created while the game was open).
Pause the scenario. Save the scenario and close Scenario Editor.

13. Open Scenario Editor again and load the scenario. The gamescript should begin to run and all of the features
should begin to populate the map. This may take several minutes for the script to finish
placing everything. When the gamescript is complete, open the Gamescript settings and remove the gamescript. 
Save the scenario. To load an existing save as a scenario, change the .sav extension to .scn and follow
the above process.

14. Load the scenario and play the game!



### Generating Map Boundaries with generate_boundary()
generate_boundary() creates a four-corner geographic boundary suitable for use with bother(). 
It supports several ways to define the desired map area.

The returned corners are always ordered:
1. Top-left
2. Top-right
3. Bottom-right
4. Bottom-left
Each coordinate pair is expressed as (latitude, longitude).

generate_boundary() returns a list of coordinate pair tuples that can be passed directly to
bother(corners=...)

#### Method 1: Top-left corner and side length

Use this method to generate a square boundary from a known top-left coordinate and side length.

```python

corners = otter.generate_boundary(
    top_left=(49.0, -124.0),
    side_length=500,
)

```

#### Method 2: Center point and radius

Use this method to generate a square boundary centered on a known geographic location.

```python 

corners = otter.generate_boundary(
    center=(37.5, -119.5),
    radius=250,
)

```

#### Method 3: Opposite corners

Use this method when the top-left and bottom-right coordinates of the desired map area are known.

```python

corners = otter.generate_boundary(
    top_left=(49.0, -124.0),
    bottom_right=(32.0, -115.0),
    bearing=0,
)

```

The function determines the dimensions and aspect ratio from the supplied diagonal. 
The optional bearing controls the orientation of the generated boundary. 
If the inferred aspect ratio is not compatible with OpenTTD's power-of-two map ratios, the function warns the user but still returns the boundary.


#### Method 4: Top edge and explicit aspect ratio

Use this method when the top edge and desired map proportions are known.

```python

corners = otter.generate_boundary(
    top_left=(49.0, -124.0),
    top_right=(49.0, -115.0),
    aspect_ratio=1 / 2,
)

```

The aspect ratio is width divided by height. Explicit ratios must be OpenTTD-compatible powers of two, 
1:64 through 64:1 (1:256 through 256:1 for JGR Patch).



### Generating Heightmaps with Custom corners

bother() can generate a heightmap from four geographic corner coordinates using the corners argument.

The four corners define the boundary of the output raster. They must form a valid convex quadrilateral and be provided in this order:
- Top-left
- Top-right
- Bottom-right
- Bottom-left
Unlike the legacy bounds interface, the corners do not have to define a north-oriented rectangle. They can describe rotated or otherwise non-rectangular convex boundaries.

The output raster is warped to the dimensions specified by scale_image. Its geographic aspect ratio does not need to match the output image aspect ratio.

#### Example 1: Use a generated boundary

```python

import otter

corners = otter.generate_boundary(
    top_left=(49.0, -124.0),
    bottom_right=(32.0, -115.0),
    bearing=0,
)

otter.bother(
    corners=corners,
    outfile="heightmap.png",
    outfile_tif="heightmap.tif",
    epsg="4326",
    scale_image="2048x1024",
    raise_undersea=True,
    raise_low=True,
)

```

#### Example 2: Supply custom corners directly

```python 

corners = [
    (49.0, -124.0),  # top-left
    (49.0, -115.0),  # top-right
    (32.0, -114.0),  # bottom-right
    (31.0, -125.0),  # bottom-left
]

otter.bother(
    corners=corners,
    outfile="custom_heightmap.png",
    outfile_tif="custom_heightmap.tif",
    epsg="4326",
    scale_image="2048x1024",
)

```

Important considerations:
- Exactly four coordinate pairs must be supplied.
- Coordinates are (latitude, longitude).
- The order must be top-left, top-right, bottom-right, bottom-left.
- The points must define a valid convex quadrilateral. Concave or self-intersecting boundaries are not supported.
- scale_image is required when using corners and specifies the output width and height in pixels.
- The output raster is warped to the requested dimensions using all four corners.
- The old bounds argument is retained for backward compatibility but is deprecated. Use corners for new projects.


<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Additional Features

### Data Types

Many functions in otter are designed to take in a variety of data types including:
- list or lists of lists (e.g. list of lat,long pairs)
- Pandas Dataframes
- Geopandas GeoDataframes
- Paths to CSV and Excel files
- Paths to shapefiles

For data inputs with tables (e.g. Excel, CSV, Shapefiles), otter provides a method to filter
the data dynamically rather than needing to filter the data in the source file or
before the function calls. Look for variables named *select_col* and *select_val* 
which define the field name to check
and the value(s) to filter table rows, respectively. 


### convert_geojson()

This function convert raw geojson outputs from [Overpass Turbo](https://overpass-turbo.eu/)
into Excel, CSV, or shapefile ouputs. Thus, city and town location and population data 
from Overpass Turbo can be converted into user-friendly and otter-friendly formats for editting
and maniupulation.

```python
convert_geojson(geojason_path, # path to a geojson file
                outpath=None, # optional, output file path for Excel, CSV, or shapefile. File type inferred from file exension.
                cols=['name','population','longitude','latitude'], # optional, a list of columns to keep from the raw geojson
# returns a geopandas GeoDataFrame. If outpath is not None, a file is also written.
```



### get_latlong_from_map()

This function converts row,column game-grid coordinates from a known, georeferenced heightmap
back to latitude (Y, column) and longitude (X, row). The game-grid coordinates must
be from a map created from the same input heightmap and GeoTIFF.

```python
get_latlong_from_map(ras, # raster GeoTIFF from Bother
                     grid_coords, # data structure containing row and column indices (shapefile, CSV, Excel, Dataframe, or list of list pairs)
                     outpath, # optional, a file path to write the output table
                     row_col, # optional, name of the table column containing row indices
                     col_col, # optional, name of the table column containing the column indices
                     select_col, # optional, name of the column to filter data
                     select_val) # optional, value to check select_col to filter data
# returns a dataframe with the longitude and latitude coordinates
```

### town_data_to_json()

This function converts town data from a common data structure into a .json file 
compatible with the new town import from file feature in the Scenario Builder.
The row,col data can be obtained using get_map_coords().

```python
town_data_to_json(town_data, # data structure containing town data (shapefile, CSV, Excel, or Dataframe)
                  map_width, # width of the intended map to convert coordinates. OTTD maps are described as width x height (clockwise)
                  map_height, # height of the intended map to convert coordinates. OTTD maps are described as width x height (clockwise)
                  json_outfile, # full file path for the output .json file with .json extension
                  name_field='name', # name of the data field containing the town name
                  pop_field='population', # name of the data field containing the town population
                  city_field='city', # name of the data field containing true/false if the town should be a city
                  x_field='row', # name of the data field containing the x coordinate (row)
                  y_field='col', # name of the data field containing the y coordinate (col)
                  select_col=None,
                  select_val=None)
```

### create_random_points()

This function helps to create random points that could be used for industry, town, or object placement.
This function requires more advanced knowledge of GIS and takes in a shapefile defining zones
to create the random points. You can specify the generation method, number of points, and
other parameters used (sample_points from GeoPandas[https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.sample_points.html])

```python
create_random_points(ras, # raster tif created by bother
                     zone_shp_path, # shapefile defining zone polygons
                     zone_col, # shapefile attribute field with zone IDs
                     methods=None, # random sampling method, defaults to 'uniform'
                     outpath=None, # file path to save the output as CSV, Excel, or shapefile
                     **kwargs, # keywrod arguments as dictionaries with sampling parameters
                    )

```

<!-- Known Issues -->
## Known Issues
- Even in Deity Mode, construction costs are still applied to Company 1 if the construction
is done through a gamescript. The current solution is to add the maximum funds before construction
and then reset the bank balance to the starting balance. However, this transaction
is still reflected in the company finances for the first year after the scenario is saved and loaded.
- Ownership of canal tiles are still assigned to Company 1 even when Deity Mode is used to place them.
This can create issues when infrastructure maintenance is turned on.


<!-- Future -->
## Future

Planned features and revisions:
- **TEST FOR OTTD 15.x and 16.x**
- Create templates and methods for extracting tile information from existing saves/scenarios
    - extract list of towns with population, tile coordinates, and house and road layouts (tiles)
    - extract list of industry, nearest town, and tile coordinates
    - extract objects, signs, and other features
- Creates templates and methods for extracting newGRF data into usable formats (not all newGRF data is publicly or easily available)
- Upload industry code references for common industry replacement sets
- Boundaries Generation:
    - output validation information
    - allow cardinal directions as inputs
    - add metadata to ouput shapefile
    - add interactive preview?

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License.

MIT License

Copyright (c) 2026 Unit01-TestType

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Unit01-TestType (DM on OpenTTD Discord)

Project Link: [https://github.com/Unit01-TestType/otter](https://github.com/Unit01-TestType/otter)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

Huge thanks and credit to Bunburya for development of Bother which is modified and included in Otter.
[https://github.com/bunburya/bother](https://github.com/bunburya/bother)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

<!-- Shields.io badges. You can a comprehensive list with many more badges at: https://github.com/inttter/md-badges -->
