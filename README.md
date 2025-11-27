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
    <li><a href="#future">Future</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->

## About the Project
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
    
    ## define the bounding box
    ## the format is: latitude bottom left, longitude bottom left, latitude top right, longitude top right
    bounds = [29.0001388888888840, -124.8155385698191395, 49.0001388888888840, -114.8155385698191395]
    otter.bother(bounds=bounds,
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
    outdir = 'C:\Users\[name]\Documents\OpenTTD\game\CA-townplacer3'
    
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

<!-- Future -->
## Future

Planned features and revisions:
- Overhaul and fix tools for random point generation
- Add tools to automatically obtain and download city information based on bounding boxes
- Refactor gamescript code so it looks like it was written by somemone who knows what they're doing...
- Create templates and methods for extracting tile information from existing saves/scenarios
    - extract list of towns with population, tile coordinates, and house and road layouts (tiles)
    - extract list of industry, nearest town, and tile coordinates
    - extract objects, signs, and other features
- Creates templates and methods for extracting newGRF data into usable formats (not all newGRF data is publicly or easily available)
- Upload industry code references for common industry replacement sets

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

Copyright (c) 2025 Unit01-TestType

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
