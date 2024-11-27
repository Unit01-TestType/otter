'''
This script contains the functions needed to build main.nut for the custom map gamescript
This is based on boiler plate provided by MinimalGS from Leif Linse.

The boiler plate was editted to include custom functions to for adding towns and industries to user-specified locations.

TODO:
    - move add towns and add industry to their own package functions; call them at the right place in build_main
    - rearrange TryIndustry to have coordinates first like TryTown
    - edit TryTown to make target_pop optional
    - add more options to input data for towns and industry (e.g. dictionary)
'''


import os
import pandas as pd

def build_main(outdir, towns, industry, 
               town_x_header='X', town_y_header='Y', town_size_header='Size',
               city_header='City',town_name_header='Name',town_pop_header='Population',
               ind_x_header='X',ind_y_header='Y',ind_name_header='Name',ind_type_header='Type'):
    '''
    This function builds main.nut file for a custom map gamescript. This file contains the main
    logic used in the gamescript. A user may provide a set of towns and industries to specifically
    place on the custom map at precise locations. This function should be used in conjunction with
    other ttnut tools to create the terrain map and extract the tile indices for towns and industries.
    

    Parameters
    ----------
    outdir : str, path
        Output directory to write the main.nut file.
    towns : list, dataframe, xlsx, csv
        A data structure or path to xlsx or csv file containing the information needed to place towns.
        Each entry must contain: tile X, tile Y, size (small, medium, large), boolean for city, unique name, and target population
    industry : list, dataframe, xlsx, csv
        A data structure or path to xlsx or csv file containing the information needed to place towns.
        Each entry must contain a unique name, X tile, Y tile, type code
    town_x_header : str, optional
        Name or index of the town X tile field header in the dataframe, xlsx, or CSV file. The default is 'X'.
    town_y_header : str, optional
        Name or index of the town Y tile field header in the dataframe, xlsx, or CSV file. The default is 'Y'.
    town_size_header : str, optional
        Name or index of the town size field header in the dataframe, xlsx, or CSV file. The default is 'Size'.
    city_header : str, optional
        Name or index of the city flag field header in the dataframe, xlsx, or CSV file. The default is 'City'.
    town_name_header : str, optional
        Name or index of the town name field header in the dataframe, xlsx, or CSV file. The default is 'Name'.
    town_pop_header : str, optional
        Name or index of the town target population field header in the dataframe, xlsx, or CSV file. The default is 'Population'. If None, this is ignored.
    ind_x_header : str, optional
        Name or index of the industry X tile field header in the dataframe, xlsx, or CSV file. The default is 'X'.
    ind_Y_header : str, optional
        Name or index of the industry Y tile field header in the dataframe, xlsx, or CSV file. The default is 'Y'.
    ind_name_header : str, optional
        Name or index of the industry name field header in the dataframe, xlsx, or CSV file. The default is 'Name'.
    ind_type_header : str, optional
        Name or index of the industry type field header in the dataframe, xlsx, or CSV file. The default is 'Type'.

    Returns
    -------
    None.

    '''
    
    #### Input error handling
    if not os.path.isdir(outdir):
        raise Exception('outdir must be valid directory.')
        
    
    '''
    - check if town and industry inputs are list of lists, dataframes, xlsx, or csv
    - check if provided headers are str name or numeric indices
        - if str name use .loc
        - if numeric, use .iloc
    '''
    
    ### Check town data structures
    if isinstance(towns, list):
        for e in towns:
            if not isinstance(e, list):
                raise ValueError('Town list input must be a list of lists')
        ## Check length of elements of list of lists
        it = iter(towns)
        the_len = len(next(it))
        if the_len > 6:
            raise ValueError('Lists must not have more than 6 values values')
        if the_len < 5:
            raise ValueError('Lists must not have fewer than 5 values values')
        if not all(len(l) == the_len for l in it):
            raise ValueError('Town list of lists must be the same length')
    
    
    ## check if xlsx or csv first, read into dataframe to check with dataframes
    if isinstance(towns, str):
        if not os.path.isfile(towns):
            raise ValueError('towns path must be a valid xlsx or csv file.')
        if os.path.splitext(os.path.basename(towns))[1] == '.xlsx':
            towns = pd.read_excel(towns) # assumes 1 sheet
        if os.path.splitext(os.path.basename(towns))[1] == '.csv':
            towns = pd.read_csv(towns)

    
    ## check if dataframe and valid column header names or indices
    if isinstance(towns, pd.DataFrame):
        if not town_x_header.isnumeric():
            if not town_x_header in towns.columns:
                raise ValueError('town_x_header must be valid column name')
        if not town_y_header.isnumeric():
            if not town_y_header in towns.columns:
                raise ValueError('town_y_header must be valid column name')
        if not town_size_header.isnumeric():
            if not town_size_header in towns.columns:
                raise ValueError('town_size_header must be valid column name')
        if not city_header.isnumeric():
            if not city_header in towns.columns:
                raise ValueError('city_header must be valid column name')
        if not town_name_header.isnumeric():
            if not town_name_header in towns.columns:
                raise ValueError('town_name_header must be valid column name')
        
        ## population target optional
        if town_pop_header is not None:
            if not town_pop_header.isnumeric():
                if not town_pop_header in towns.columns:
                    raise ValueError('town_pop_header must be valid column name')
                    
    
    
    ### Check industry data structures
    if isinstance(industry, list):
        for e in industry:
            if not isinstance(e, list):
                raise ValueError('ind list input must be a list of lists')
        ## Check length of elements of list of lists
        it = iter(industry)
        the_len = len(next(it))
        if the_len > 6:
            raise ValueError('Lists must not have more than 6 values values')
        if the_len < 5:
            raise ValueError('Lists must not have fewer than 5 values values')
        if not all(len(l) == the_len for l in it):
            raise ValueError('ind list of lists must be the same length')
    
    
    ## check if xlsx or csv first, read into dataframe to check with dataframes
    if isinstance(industry, str):
        if not os.path.isfile(industry):
            raise ValueError('industry path must be a valid xlsx or csv file.')
        if os.path.splitext(os.path.basename(industry))[1] == '.xlsx':
            industry = pd.read_excel(industry) # assumes 1 sheet
        if os.path.splitext(os.path.basename(industry))[1] == '.csv':
            industry = pd.read_csv(industry)

    
    ## check if dataframe and valid column header names or indices
    if isinstance(industry, pd.DataFrame):
        if not ind_x_header.isnumeric():
            if not ind_x_header in industry.columns:
                raise ValueError('ind_x_header must be valid column name')
        if not ind_y_header.isnumeric():
            if not ind_y_header in industry.columns:
                raise ValueError('ind_y_header must be valid column name')
        if not ind_name_header.isnumeric():
            if not ind_name_header in industry.columns:
                raise ValueError('ind_name_header must be valid column name')
        if not ind_type_header.isnumeric():
            if not ind_type_header in industry.columns:
                raise ValueError('ind_type_header must be valid column name')

    
    
    
    
    
    
    #### Begin writing file
    main_file = open(os.path.join(outdir,'main.nut'),'w')
    
    
    l1 = [
         '/** Import SuperLib for GameScript **/\n',
         'import("util.superlib", "SuperLib", 36);\n'
         'Result <- SuperLib.Result;\n',
         'Log <- SuperLib.Log;\n',
         'Helper <- SuperLib.Tile;\n',
         'Tile <- SuperLib.Direction;\n',
         'Town <- SuperLib.Town;\n',
         'Industry <- SuperLib.Industry;\n',
         'Story <- SuperLib.Story;\n',
         '// Additional SuperLib sub libraries can be found here:\n',
         '// http://dev.openttdcoop.org/projects/superlib/repository\n\n',
         '/** Import other libs **/\n',
         '// There are several other libraries for Game Scripts out there. Check out\n',
         '// http://bananas.openttd.org/en/gslibrary/ for an up to date list.\n',
         '//\n',
         '// Remember to set dependencies in the bananas web manager for all libraries\n',
         '// that you use. This way users will automatically get all libraries of the\n',
         '// version you selected when they download your Game Script.\n\n\n',
         '/** Import other source code files **/\n',
         'require("version.nut"); // get SELF_VERSION\n',
         '//require("some_file.nut");\n\n\n',
         'class MainClass extends GScontroller\n',
         '{\n',
         '\t_loaded_data = null;\n',
         '\t_loaded_from_version = null;\n',
         '\t_init_done = null;\n\n',
         '\t/*\n',
         '\t * This method is called when your GS is constructed.\n',
         '\t * It is recommended to only do basic initialization of member variables\n',
         '\t * here.\n',
         '\t * Many API functions are unavailable from the constructor. Instead do\n',
         '\t * or call most of your initialization code from MainClass::Init.\n',
         '\t */\n',
     	'\tconstructor()\n',
        '\t{\n'
        '\t\tthis._init_done = false;\n',
        '\t\tthis._loaded_data = null;\n',
        '\t\tthis._loaded_from_version = null;\n',
        '\t}\n',
        '}\n\n',
        '/*\n',
        ' * This method is called by OpenTTD after the constructor, and after calling\n',
        ' * Load() in case the game was loaded from a save game. You should never\n',
        ' * return back from this method. (if you do, the script will crash)\n',
        ' *\n',
        ' * Start() contains of two main parts. First initialization (which is\n',
        ' * located in Init), and then the main loop.\n',
        ' */\n',
        'function MainClass::Start()\n',
        '{\n',
        '\t// Some OpenTTD versions are affected by a bug where all API methods\n',
    	'\t// that create things in the game world during world generation will\n',
    	'\t// return object id 0 even if the created object has a different ID.\n' ,
    	'\t// In that case, the easiest workaround is to delay Init until the\n',
    	'\t// game has started.\n',
    	'\tif (Helper.HasWorldGenBug()) GSController.Sleep(1);\n\n',
    	'\tthis.Init();\n\n',
    	'\t// Wait for the game to start (or more correctly, tell OpenTTD to not\n',
    	'\t// execute our GS further in world generation)\n',
    	'\tGSController.Sleep(1);\n\n',
    	'\t// Game has now started and if it is a single player game,\n',
    	'\t// company 0 exist and is the human company.\n\n',
    	'\t// Main Game Script loop\n'
         ]

    main_file.writelines(l1)
    
    #### Add towns
    
    ## if list of lists, loop through main list, values must be in the right order:
        # X, Y, size, city_flag, name, pop
    if isinstance(towns, list):
        for t in towns:
            town_x = t[0]
            town_y = t[1]
            town_size = t[2]
            town_city = t[3]
            town_name = str(t[4])
            
            if len(t) == 6:
                town_pop = t[5]
                try:
                    town_pop = int(round(float(town_pop),0))
                    town_pop = str(town_pop)
                except:
                    print('Error: Target population tile must be integer. Skipping.')
                    continue
            else:
                town_pop = '0' # ignore value
            
            try:
                town_x = int(town_x)
                town_x = str(town_x)
            except:
                print('Error: X tile must be integer. Skipping.')
                continue
            try:
                town_y = int(town_y)
                town_y = str(town_y)
            except:
                print('Error: Y tile must be integer. Skipping.')
                continue
            
            try:
                town_size = str(town_size).upper()
            except:
                print('Error: town size must be SMALL, MEDIUM, or LARGE. Skipping.')
                continue
            
            if town_size not in ['SMALL','MEDIUM','LARGE']:
                print('Error: town size must be SMALL, MEDIUM, or LARGE. Skipping.')
                continue
            else:
                if town_size == 'SMALL':
                    town_size = 'GSTown.TOWN_SIZE_SMALL'
                if town_size == 'MEDIUM':
                    town_size = 'GSTown.TOWN_SIZE_MEDIUM'
                if town_size == 'LARGE':
                    town_size = 'GSTown.TOWN_SIZE_LARGE'
                
            try:
                town_city = str(town_city).lower()
            except:
                print('Error: city flag must be true or false. Skipping.')
                continue
            
            if town_city not in ['true','false']:
                print('Error: city flag must be true or false. Skipping.')
                continue
            
        
            main_file.write('\tTryTown('+town_x+','+town_y+','+town_size+','+town_city+','+town_name+','+town_pop+');\n')
                
    
    ## route for dataframes
    elif isinstance(towns, pd.DataFrame):
        for index, row in towns.iterrows():
            
            ## check if index or name
            if town_x_header.isnumeric():
                town_x = row.iloc[town_x_header]
            else:
                town_x = row[town_x_header]
                
            if town_y_header.isnumeric():
                town_y = row.iloc[town_y_header]
            else:
                town_y = row[town_y_header]
            
            if town_size_header.isnumeric():
                town_size = row.iloc[town_size_header]
            else:
                town_size = row[town_size_header]
            
            if city_header.isnumeric():
                town_city = row.iloc[city_header]
            else:
                town_city = row[city_header]
                
            if town_name_header.isnumeric():
                town_name = row.iloc[town_name_header]
            else:
                town_name = row[town_name_header]
            
            if town_pop_header is not None:
                if town_pop_header.isnumeric():
                    town_pop = row.iloc[town_pop_header]
                else:
                    town_pop = row[town_pop_header]
            else:
                town_pop = '0' # ignore value
                
                
            ## check values
            try:
                town_x = int(town_x)
                town_x = str(town_x)
            except:
                print('Error: X tile must be integer. Skipping.')
                continue
            try:
                town_y = int(town_y)
                town_y = str(town_y)
            except:
                print('Error: Y tile must be integer. Skipping.')
                continue
            
            try:
                town_size = str(town_size).upper()
            except:
                print('Error: town size must be SMALL, MEDIUM, or LARGE. Skipping.')
                continue
            
            if town_size not in ['SMALL','MEDIUM','LARGE']:
                print('Error: town size must be SMALL, MEDIUM, or LARGE. Skipping.')
                continue
            else:
                if town_size == 'SMALL':
                    town_size = 'GSTown.TOWN_SIZE_SMALL'
                if town_size == 'MEDIUM':
                    town_size = 'GSTown.TOWN_SIZE_MEDIUM'
                if town_size == 'LARGE':
                    town_size = 'GSTown.TOWN_SIZE_LARGE'
                
            try:
                town_city = str(town_city).lower()
            except:
                print('Error: city flag must be true or false. Skipping.')
                continue
            
            if town_city not in ['true','false']:
                print('Error: city flag must be true or false. Skipping.')
                continue
            
            try:
                town_pop = int(round(float(town_pop),0))
                town_pop = str(town_pop)
            except:
                print('Error: Target population tile must be integer. Skipping.')
                continue
                
        
            
            main_file.write('\tTryTown('+town_x+','+town_y+','+town_size+','+town_city+','+town_name+','+town_pop+');\n')
    
    
    main_file.write('\n\tprint("Finished adding towns. Adding industries.")\n\n')
    
    
    #### Add industries
    
    
    main_file.close()
    
    
    
    
    
    
    
    