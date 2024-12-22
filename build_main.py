'''
This script contains the functions needed to build main.nut for the custom map gamescript
This is based on boiler plate provided by MinimalGS from Leif Linse.

The boiler plate was editted to include custom functions to for adding towns and industries to user-specified locations.

TODO:
    - add more options to input data for towns and industry (e.g. dictionary)
    
    - add options to add place labels

'''


import os
import pandas as pd
import warnings


#### Main function to build main.nut
def build_main(outdir, towns_code=None, industry_code=None, canal_code=None):
    '''
    This function builds main.nut file for a custom map gamescript. 

    Parameters
    ----------
    outdir : str, path
        Output directory to write the main.nut file.
    towns_code : list
        A list containing formatted string to add town line code.
    industry_code : list
        A list containing formatted string to add industry line code.
    canal_code : list
        A list containing formatted string to add canal line code.

    Returns
    -------
    None.

    '''
    
    print('Building main.nut...')
    
    #### Input error handling
    if not os.path.isdir(outdir):
        raise Exception('outdir must be valid directory.')
    
    
    
    #### Begin writing file
    main_file = open(os.path.join(outdir,'main.nut'),'w')
    
    
    l1 = [
          '/*\n'
          ' * This file is part of MinimalGS, which is a GameScript for OpenTTD\n',
          ' * Copyright (C) 2012-2013  Leif Linse\n',
          ' *\n',
          ' * MinimalGS is free software; you can redistribute it and/or modify it\n' ,
          ' * under the terms of the GNU General Public License as published by\n',
          ' * the Free Software Foundation; version 2 of the License\n',
          ' *\n',
          ' * MinimalGS is distributed in the hope that it will be useful,\n',
          ' * but WITHOUT ANY WARRANTY; without even the implied warranty of\n',
          ' * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n',
          ' * GNU General Public License for more details.\n',
          ' *\n',
          ' * You should have received a copy of the GNU General Public License\n',
          ' * along with MinimalGS; If not, see <http://www.gnu.org/licenses/> or\n',
          ' * write to the Free Software Foundation, Inc., 51 Franklin Street,\n',
          ' * Fifth Floor, Boston, MA 02110-1301 USA.\n',
          ' *\n',
          ' */\n\n',
         '/** Import SuperLib for GameScript **/\n',
         'import("util.superlib", "SuperLib", 36);\n'
         'Result <- SuperLib.Result;\n',
         'Log <- SuperLib.Log;\n',
         'Helper <- SuperLib.Helper;\n',
         'Tile <- SuperLib.Tile;\n',
         'Direction <- SuperLib.Direction;\n'
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
         'class MainClass extends GSController\n',
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
        '\tGSGame.Pause();\n\n',
    	'\t// Main Game Script loop\n'
         ]

    main_file.writelines(l1)
    
    #### Add towns
    if towns_code is not None:
        main_file.writelines(towns_code)
        main_file.write('\n\tprint("Finished adding towns.");\n\n')
    
    
    #### Add industries
    if industry_code is not None:
        main_file.write('\tlocal bank_balance = GSCompany.ChangeBankBalance(0,9990000000,7,GSMap.TILE_INVALID);\n')
        main_file.writelines(industry_code)
        main_file.write('\n\tprint("Finished adding industries.");\n\n')
        main_file.write('\t// set bank balance back to starting balance\n')
        main_file.write('\tbank_balance = GSCompany.GetBankBalance(0);\n')
        main_file.write('\tlocal bb_diff = (bank_balance - 100000);\n')
        main_file.write('\tbank_balance = GSCompany.ChangeBankBalance(0,-1*bb_diff,0,GSMap.TILE_INVALID);\n\n')
        
    
    #### Add canals
    if canal_code is not None:
        main_file.write('\t// Start in deity mode to add funds. Then change to company mode to place canals.\n')
        main_file.write('\tlocal bank_balance = GSCompany.ChangeBankBalance(0,9990000000,7,GSMap.TILE_INVALID);\n')
        main_file.writelines(canal_code)
        main_file.write('\n\tprint("Finished adding canals.");\n\n')
        main_file.write('\t// set bank balance back to starting balance\n')
        main_file.write('\tbank_balance = GSCompany.GetBankBalance(0);\n')
        main_file.write('\tlocal bb_diff = (bank_balance - 100000);\n')
        main_file.write('\tbank_balance = GSCompany.ChangeBankBalance(0,-1*bb_diff,0,GSMap.TILE_INVALID);\n\n')

    
    #### End of main script loop
    main_file.write('\tprint("Finish");\n\n')
    main_file.write('\n\tGSGame.Unpause();\n\n\n')
    main_file.write('}\n\n')
    
    
    l2 = [
         '/*\n',
         ' * This method is called during the initialization of your Game Script.\n',
         ' * As long as you never call Sleep() and the user got a new enough OpenTTD\n',
         " * version, all initialization happens while the world generation screen\n",
         " * is shown. This means that even in single player, company 0 doesn't yet\n",
         ' * exist. The benefit of doing initialization in world gen is that commands\n',
         ' * that alter the game world are much cheaper before the game starts.\n',
         '*/\n',
         'function MainClass::Init()\n',
         '{\n',
    	 '\tif (this._loaded_data != null) {\n',
    	 '\t\t// Copy loaded data from this._loaded_data to this.*\n',
    	 '\t\t// or do whatever you like with the loaded data\n',
    	 '\t} else {\n',
    	 '\t\t// construct goals etc.\n',
    	 '\t}\n\n',
    	 '\t// Indicate that all data structures has been initialized/restored.\n',
    	 '\tthis._init_done = true;\n',
    	 '\tthis._loaded_data = null; // the loaded data has no more use now after that _init_done is true.\n',
         '}\n\n\n\n',
         
         
         
         '/*\n',
         ' * This method handles incoming events from OpenTTD.\n',
         ' */\n',
         'function MainClass::HandleEvents()\n',
         '{\n',
         '\tif(GSEventController.IsEventWaiting()) {\n',
		 '\t\tlocal ev = GSEventController.GetNextEvent();\n',
		 '\t\tif (ev == null) return;\n\n',
		 '\t\tlocal ev_type = ev.GetEventType();\n',
		 '\t\tswitch (ev_type) {\n',
		 '\t\t\tcase GSEvent.ET_COMPANY_NEW: {\n',
		 '\t\t\t\tlocal company_event = GSEventCompanyNew.Convert(ev);\n',
		 '\t\t\t\tlocal company_id = company_event.GetCompanyID();\n',
		 '\t\t\t\t// Here you can welcome the new company\n',
		 '\t\t\t\tStory.ShowMessage(company_id, GSText(GSText.STR_WELCOME, company_id));\n',
		 '\t\t\t\tbreak;\n',
		 '\t\t\t}\n\n',
		 '\t\t\t// other events ...\n',
		 '\t\t}\n',
	     '\t}\n',
         '}\n\n\n',
         
         
         '/*\n',
         ' * Called by our main loop when a new month has been reached.\n',
         ' */\n',
         'function MainClass::EndOfMonth()\n',
         '{\n',
         '}\n\n',
         
         '/*\n',
         ' * Called by our main loop when a new year has been reached.\n',
         ' */\n',
         'function MainClass::EndOfYear()\n',
         '{\n',
         '}\n\n',
         
         '/*\n',
         ' * This method is called by OpenTTD when an (auto)-save occurs. You should\n',
         ' * return a table which can contain nested tables, arrays of integers,\n',
         ' * strings and booleans. Null values can also be stored. Class instances and\n',
         ' * floating point values cannot be stored by OpenTTD.\n',
         ' */\n',
         'function MainClass::Save()\n',
         '{\n',
         '\tLog.Info("Saving data to savegame", Log.LVL_INFO);\n\n',
         '\t// In case (auto-)save happens before we have initialized all data,\n',
         '\t// save the raw _loaded_data if available or an empty table.\n',
         '\tif (!this._init_done) {\n',
         '\t\treturn this._loaded_data != null ? this._loaded_data : {};\n',
         '\t}\n\n',
         '\treturn {\n' ,
         '\t\tsome_data = null,\n',
         '\t\t//some_other_data = this._some_variable,\n',
         '\t};\n',
         '}\n\n',
         
         '/*\n',
         ' * When a game is loaded, OpenTTD will call this method and pass you then\n',
         ' * table that you sent to OpenTTD in Save().\n',
         ' */\n',
         'function MainClass::Load(version, tbl)\n',
         '{\n',
         '\tLog.Info("Loading data from savegame made with version " + version + " of the game script", Log.LVL_INFO);\n\n',
	     '\t// Store a copy of the table from the save game\n',
	     '\t// but do not process the loaded data yet. Wait with that to Init\n',
	     "\t// so that OpenTTD doesn't kick us for taking too long to load.\n",
	     '\tthis._loaded_data = {}\n',
   	     '\tforeach(key, val in tbl) {\n',
		 '\t\tthis._loaded_data.rawset(key, val);\n',
	     '\t}\n\n',
	     '\tthis._loaded_from_version = version;\n',
         '}\n\n\n\n\n',
         
         
         
         #### TryTown Function
         'function MainClass::TryTown(x, y, size, city, name, target_pop) {\n',
             '\tlocal success = false;\n',
             '\tlocal timeout = 1000;\n',
             '\tlocal counter = 0;\n',
             '\tlocal exp = false;\n\n',

         '\twhile(!success && counter < timeout) {\n',
             '\t\tlocal cur_tile = GSMap.GetTileIndex(x, y);\n',
             '\t\tsuccess = GSTown.FoundTown(cur_tile, size, city, GSTown.ROAD_LAYOUT_BETTER_ROADS, name);\n',
    		 '\t\t// move coordinates around until it places\n',
             '\t\tx = x + GSBase.RandRange(3) - 1;\n',
             '\t\ty = y + GSBase.RandRange(3) - 1;\n',
             '\t\tcounter += 1;\n',
         '\t}\n\n',
	
    	 '\t// Grow pop if town is built\n',
         '\tif(success) {\n',
    		 '\t\tif(target_pop > 0) {\n',
    			 '\t\t\tlocal town_id = GSTownList(); // full list of ids\n',
    			 '\t\t\tlocal pop = GSTown.GetPopulation(town_id.Begin()); // get population of most recent town with most recent id\n',
    			 '\t\t\tif(pop < target_pop) {\n',
    				 '\t\t\t\tlocal nhouses  = (target_pop - pop)/10;\n' ,
    				 '\t\t\t\tif(nhouses > 1) {\n',
    					 '\t\t\t\t\texp = GSTown.ExpandTown(town_id.Begin(), nhouses);\n',
    						 '\t\t\t\t\t\tif(!success) {\n',
    							 '\t\t\t\t\t\t\tGSLog.Warning(name);\n',
    						 '\t\t\t\t\t\t}\n',
    				 '\t\t\t\t}\n',
    			 '\t\t\t}\n',
    		 '\t\t}\n',
	     '\t}\n\n',
	
         '\tif(!success) {\n',
             '\t\tGSLog.Warning(name);\n',
         '\t}\n\n',
		
         '}\n\n\n',
         
         
         
         ##### TryIndustry Function
         'function MainClass::TryIndustry(x, y, name, type, trylevel, level_x2, level_y2) {\n',
        	 '\tlocal success = false;\n',
             '\tlocal timeout = 2000;\n',
             '\tlocal counter = 0;\n\n',
        
        	 '\tlocal cur_tile = GSMap.GetTileIndex(x, y);\n',
        	 '\tsuccess = GSIndustryType.BuildIndustry(type, cur_tile);\n\n',
        
        	 '\tif(success) {\n',
        		 '\t\t// print("Success");\n',
                 '\t\treturn success;\n'
        	 '\t} else {\n',
        		 '\t\tif (trylevel) {\n\n',
        
        		 '\t\t\tlocal x2 = x + level_x2 + 1;\n',
        		 '\t\t\tlocal y2 = y + level_y2 + 1;\n',
        		 '\t\t\tlocal level_success = false;\n',
        		 '\t\t\tlevel_success = LevelTiles(x, y, x2, y2)\n\n',
        
        		 '\t\t\tif (level_success) {\n',
        			 '\t\t\t\tsuccess = GSIndustryType.BuildIndustry(type, cur_tile);\n',
    				 '\t\t\t\twhile(!success && counter < timeout) {\n'
    					 '\t\t\t\t\tcur_tile = GSMap.GetTileIndex(x, y);\n'
    					 '\t\t\t\t\tsuccess = GSIndustryType.BuildIndustry(type, cur_tile);\n'
    					 '\t\t\t\t\t// move coordinates around until it places\n'
    					 '\t\t\t\t\tlocal x = x + GSBase.RandRange(3) - 1;\n'
    					 '\t\t\t\t\tlocal y = y + GSBase.RandRange(3) - 1;\n'
    					 '\t\t\t\t\tcounter += 1;\n'
    				 '\t\t\t\t}\n'		
        			 '\t\t\t\tif (success) {\n',
        				 '\t\t\t\t\t//print("Successfully added industry after leveling.");\n',
        			 '\t\t\t\t} else {\n',
        				 '\t\t\t\t\tprint("Failed to add industry after leveling: " + name);\n',
        			 '\t\t\t\t}\n',
        		 '\t\t\t} else {\n',
        			 '\t\t\t\tprint("Leveling failed. Could not place industry: " + name);\n',
        		 '\t\t\t}\n\n',
        
          		 '\t\t} else {\n',
          			 '\t\t\twhile(!success && counter < timeout) {\n',
          				 '\t\t\t\tcur_tile = GSMap.GetTileIndex(x, y);\n',
          				 '\t\t\t\tsuccess = GSIndustryType.BuildIndustry(type, cur_tile);\n',
          				 '\t\t\t\t// move coordinates around until it places\n',
          				 '\t\t\t\tlocal x = x + GSBase.RandRange(3) - 1;\n',
          				 '\t\t\t\tlocal y = y + GSBase.RandRange(3) - 1;\n',
          				 '\t\t\t\tcounter += 1;\n',
          			 '\t\t\t}\n',
          			 '\t\t\tif (!success){\n',
          				 '\t\t\t\tprint("Failed to add industry: " + name);\n',
          			 '\t\t\t}\n',
          		 '\t\t}\n',
        	 '\t}\n\n',
        		
        	 '\treturn success;\n',
         '}\n\n\n',
         
         
         #### PlaceCanal Function
         '// function for placing canal like river and lake at elevation\n',
         'function MainClass::PlaceCanal(x, y) {\n\n',
         
             '\tlocal deity = GSCompanyMode.IsDeity();\n',
             '\tlocal companyIdx = 0;\n',
             '\tlocal cm;\n',
             '\tif (deity) {\n',
            	 '\t\tcm = GSCompanyMode(companyIdx);\n',
             '\t}\n\n',         
        	
        	 '\tlocal canal_success = false;\n',
        	 '\tlocal cur_tile = GSMap.GetTileIndex(x,y);\n',
        	 '\tcanal_success = GSMarine.BuildCanal(cur_tile);\n',
        	 # '\tif (!canal_success) {\n',
        		# '\t\t//print(">Could not build canal at " + x + " " +y);\n',
        	 # '\t}\n\n',
        	
         '}\n\n',
         
        '// function for leveling tiles\n',
        '// used to help level terrain to place industries\n',
        'function MainClass::LevelTiles(x1, y1, x2, y2) {\n\n',
        	
        	'\t// x1,y1 is the upper left corner\n',
        	'\t// x2,y2 is the lower right corner\n\n',
        	
        	'\t// print("Leveling tiles...");\n\n',
        	
        	 '\tlocal start_tile = GSMap.GetTileIndex(x1, y1);\n',
        	 '\tlocal end_tile = GSMap.GetTileIndex(x2, y2);\n',
        	 '\tlocal deity = GSCompanyMode.IsDeity();\n',
        	 '\tlocal companyIdx = 0;\n',
        	 '\tlocal cm;\n',
        	 '\tif (deity) {\n',
        		 '\t\tcm = GSCompanyMode(companyIdx);\n',
        	 '\t}\n\n',
        	
        	'\tlocal success = false;\n',
        	'\tsuccess = GSTile.LevelTiles(start_tile, end_tile);\n\n',
        	
        	'\tif (success) {\n',
        		'\t\t//print(">Leveling succeeded.");\n',
        	'\t} else {\n',
        		'\t\tprint(">Leveling failed.");\n',
        	'\t}\n\n',
        	
        	'\treturn success;\n\n',
        	
        '}'
         
         ]
    
    
    main_file.writelines(l2)
    
    main_file.close()
    
    print('Done.')
    






#### Create towns code

def build_towns_code(towns, town_x_header='X', town_y_header='Y', town_size_header='Size',
                     city_header='City',town_name_header='Name',town_pop_header='Population'):
    '''
    

    Parameters
    ----------
    towns : list, dataframe, xlsx, csv
        A data structure or path to xlsx or csv file containing the information needed to place towns.
        Each entry must contain: tile X, tile Y, size (small, medium, large), boolean for city, unique name, and target population
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

    Returns
    -------
    List of formatted string to insert into main.nut

    '''
    
    print('Building code to add towns...')
    
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
        
        match os.path.splitext(os.path.basename(towns))[1]:
            case '.xlsx':
                towns = pd.read_excel(towns) # assumes 1 sheet
            case '.csv':
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
                    
                    
        #### Add towns
        
        towns_code = [] # empty list to append
        
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
                
            
                line = '\tTryTown('+town_x+','+town_y+','+town_size+','+town_city+','+'"'+town_name+'"'+','+town_pop+');\n'
                towns_code.append(line)
        
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
                    town_name = str(row.iloc[town_name_header])
                else:
                    town_name = str(row[town_name_header])
                
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
                    
                
                line = '\tTryTown('+town_x+','+town_y+','+town_size+','+town_city+','+'"'+town_name+'"'+','+town_pop+');\n'
                towns_code.append(line)
        
        
    print('Done.')
        
    return towns_code


#### Create industries code

def build_industry_code(industry, ind_x_header='X',ind_y_header='Y',ind_name_header='Name',ind_type_header='Type',
                        trylevel_header=None, level_x2_header=None, level_y2_header=None):
    '''
    This function helps build the squirrel code function calls for TryIndustry to build industries.

    Parameters
    ----------
    industry : list, dataframe, xlsx, csv
        A data structure or path to xlsx or csv file containing the information needed to place towns.
        Each entry must contain a unique name, X tile, Y tile, type code
    ind_x_header : str, optional
        Name or index of the industry X tile field header in the dataframe, xlsx, or CSV file. The default is 'X'.
    ind_y_header : str, optional
        Name or index of the industry Y tile field header in the dataframe, xlsx, or CSV file. The default is 'Y'.
    ind_name_header : str, optional
        Name or index of the industry name field header in the dataframe, xlsx, or CSV file. The default is 'Name'.
    ind_type_header : str, optional
        Name or index of the industry type field header in the dataframe, xlsx, or CSV file. The default is 'Type'.
    trylevel_header : str, optional
        Name or index of the header containing the flag for leveling in the dataframe, xlsx, or CSV file. The defeault is 'Level'.
    level_x2_header : str, optional
        Name or index of the header containing the number of tiles down for leveling in the dataframe, xlsx, or CSV file. The defeault is 'Level'.
    level_y2_header : str, optional
        Name or index of the header containing the number of tiles across for leveling in the dataframe, xlsx, or CSV file. The defeault is 'Level'.
    
    Returns
    -------
    List of formatted string to insert into main.nut

    '''
    
    print('Building code to add industries...')
    
    ### Check industry data structures
    if isinstance(industry, list):
        for e in industry:
            if not isinstance(e, list):
                raise ValueError('ind list input must be a list of lists')
        ## Check length of elements of list of lists
        it = iter(industry)
        the_len = len(next(it))
        if the_len > 8:
            raise ValueError('Lists must not have more than 8 values values')
        if the_len < 4:
            raise ValueError('Lists must not have fewer than 4 values values')
        if not all(len(l) == the_len for l in it):
            raise ValueError('ind list of lists must be the same length')
    
    
    ## check if xlsx or csv first, read into dataframe to check with dataframes
    if isinstance(industry, str):
        if not os.path.isfile(industry):
            raise ValueError('industry path must be a valid xlsx or csv file.')
            
        match os.path.splitext(os.path.basename(industry))[1]:
            case '.xlsx':
                industry = pd.read_excel(industry) # assumes 1 sheet
            case '.csv':
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
                
        if trylevel_header is not None:
            if not trylevel_header.isnumeric():
                if not trylevel_header in industry.columns:
                    raise ValueError('trylevel_header must be valid column name')
            if not level_x2_header.isnumeric():
                if not level_x2_header in industry.columns:
                    raise ValueError('level_x2_header must be valid column name')
            if not level_y2_header.isnumeric():
                if not level_y2_header in industry.columns:
                    raise ValueError('level_y2_header must be valid column name')
    
    
    #### Add industries
    
    industry_code = [] # empty list
    
    ## if list of lists, loop through main list, values must be in the right order:
        # X, Y, name, type, trylevel, level_x2, level_y2
    if isinstance(industry, list):
        for i in industry:
            ind_x = i[0]
            ind_y = i[1]
            ind_name = str(i[2])
            ind_type = i[3]
            
            if len(industry) > 4:
                trylevel = str(i[4])
                level_x2 = i[5]
                level_y2 = i[6]
                ## these are optional
                if str(trylevel).lower() not in ['true','false']:
                    print('Error: tryelvel must be true or false. Skipping.')
                    continue
                else:
                    trylevel = str(trylevel).lower()
                
                try:
                    level_x2 = int(level_x2)
                    level_x2 = str(level_x2)
                except:
                    warnings.warn('Warning: level_x2 must be integer.')
                    level_x2 = '0'
                try:
                    level_y2 = int(level_y2)
                    level_y2 = str(level_y2)
                except:
                    warnings.warn('Warning: level_y2 must be integer.')
                    level_y2 = '0'
            else:
                trylevel = 'false'
                level_x2 = '0'
                level_y2 = '0'
                
            
            try:
                ind_x = int(ind_x)
                ind_x = str(ind_x)
            except:
                print('Error: X tile must be integer. Skipping.')
                continue
            try:
                ind_y = int(ind_y)
                ind_y = str(ind_y)
            except:
                print('Error: Y tile must be integer. Skipping.')
                continue

            try:
                ind_type = int(ind_type)
                ind_type = str(ind_type)
            except:
                print('Error: Industry type must be integer. Skipping.')
                continue
            
        
            line = '\tTryIndustry('+ind_x+','+ind_y+','+'"'+ind_name+'"'+','+ind_type+','+trylevel+','+level_x2+','+level_y2+');\n'
            industry_code.append(line)
                
    
    ## route for dataframes
    elif isinstance(industry, pd.DataFrame):
        for index, row in industry.iterrows():
            
            ## check if index or name
            if ind_x_header.isnumeric():
                ind_x = row.iloc[ind_x_header]
            else:
                ind_x = row[ind_x_header]
                
            if ind_y_header.isnumeric():
                ind_y = row.iloc[ind_y_header]
            else:
                ind_y = row[ind_y_header]
            
            if ind_name_header.isnumeric():
                ind_name = str(row.iloc[ind_name_header])
            else:
                ind_name = str(row[ind_name_header])
            
            if ind_type_header.isnumeric():
                ind_type = row.iloc[ind_type_header]
            else:
                ind_type = row[ind_type_header]
                
                
            ## optional
            if trylevel_header is not None:
                if trylevel_header.isnumeric():
                    trylevel = row.iloc[trylevel_header]
                elif trylevel_header in industry:
                    trylevel = row[trylevel_header]
                    trylevel = str(trylevel).lower()
                else:
                    trylevel = 'false'
                
                if level_x2_header.isnumeric():
                    level_x2 = row.iloc[level_x2_header]
                elif level_x2_header in industry:
                    level_x2 = row[level_x2_header]
                    try:
                        level_x2 = int(level_x2)
                        level_x2 = str(level_x2)
                    except:
                        warnings.warn('Warning: level_x2 must be integer.')
                        level_x2 = '0'
                else:
                    level_x2 = '0'
    
                if level_y2_header.isnumeric():
                    level_y2 = row.iloc[level_y2_header]
                elif level_y2_header in industry:
                    level_y2 = row[level_y2_header]
                    try:
                        level_y2 = int(level_y2)
                        level_y2 = str(level_y2)
                    except:
                        warnings.warn('Warning: level_y2 must be integer.')
                        level_y2 = '0'
                else:
                    level_y2 = '0'
            else:
                trylevel = 'false'
                level_x2 = '0'
                level_y2 = '0'
                
                
            ## check values
            try:
                ind_x = int(ind_x)
                ind_x = str(ind_x)
            except:
                print('Error: X tile must be integer. Skipping.')
                continue
            try:
                ind_y = int(ind_y)
                ind_y = str(ind_y)
            except:
                print('Error: Y tile must be integer. Skipping.')
                continue
            
            try:
                ind_type = int(ind_type)
                ind_type = str(ind_type)
            except:
                print('Error: Industry type must be integer. Skipping.')
                continue

                
            line = '\tTryIndustry('+ind_x+','+ind_y+','+'"'+ind_name+'"'+','+ind_type+','+trylevel+','+level_x2+','+level_y2+');\n'
            industry_code.append(line)
            
    
    print('Done.')
    
    return industry_code


#### Create canal code

def build_canal_code(canals, x_header='X', y_header='Y'):
    '''
    This function helps build the squierrel code function calls for PlaceCanal to place canal tiles.

    Parameters
    ----------
    canals : list, dataframe, xslx, csv
        A data structure or path to xlsx or csv file containing x,y tile coordinates to build canals.
    x_header : str, optional
        Name or index of the industry X tile field header in the dataframe, xlsx, or CSV file. The default is 'X'.
    y_header : str, optional
        Name or index of the industry Y tile field header in the dataframe, xlsx, or CSV file. The default is 'Y'.

    Returns
    -------
    List of formatted string to insert into main.nut

    '''
    
    print('Building code to add canals...')
    
    ### Check town data structures
    if isinstance(canals, list):
        for e in canals:
            if not isinstance(e, list):
                raise ValueError('Town list input must be a list of lists')
        ## Check length of elements of list of lists
        it = iter(canals)
        the_len = len(next(it))
        if the_len != 2:
            raise ValueError('Lists must have 2 values')
        if not all(len(l) == the_len for l in it):
            raise ValueError('Town list of lists must be the same length')
    
    
    ## check if xlsx or csv first, read into dataframe to check with dataframes
    if isinstance(canals, str):
        if not os.path.isfile(canals):
            raise ValueError('canals path must be a valid xlsx or csv file.')
        
        match os.path.splitext(os.path.basename(canals))[1]:
            case '.xlsx':
                canals = pd.read_excel(canals) # assumes 1 sheet
            case '.csv':
                canals = pd.read_csv(canals)
    
    ## check if dataframe and valid column header names or indices
    if isinstance(canals, pd.DataFrame):
        if not x_header.isnumeric():
            if not x_header in canals.columns:
                raise ValueError('x_header must be valid column name')
        if not y_header.isnumeric():
            if not y_header in canals.columns:
                raise ValueError('y_header must be valid column name')
        
        #### Add canals
        
        canal_code = [] # empty list to append
        
        ## if list of lists, loop through main list, values must be in the right order:
            # X, Y
        if isinstance(canals, list):
            for c in canals:
                canal_x = c[0]
                canal_y = c[1]
                
                try:
                    canal_x = int(canal_x)
                    canal_x = str(canal_x)
                except:
                    print('Error: X tile must be integer. Skipping.')
                    continue
                try:
                    canal_y = int(canal_y)
                    canal_y = str(canal_y)
                except:
                    print('Error: Y tile must be integer. Skipping.')
                    continue
                
            
                line = '\tPlaceCanal('+canal_x+','+canal_y+');\n'
                canal_code.append(line)
        
        ## route for dataframes
        elif isinstance(canals, pd.DataFrame):
            for index, row in canals.iterrows():
                
                ## check if index or name
                if x_header.isnumeric():
                    canal_x = row.iloc[x_header]
                else:
                    canal_x = row[x_header]
                    
                if y_header.isnumeric():
                    canal_y = row.iloc[y_header]
                else:
                    canal_y = row[y_header]
                    
                
                ## check if multiple row,col pairs given for a single row
                ## if lists, loop through the pairs in the list
                if (isinstance(canal_x, list) and not isinstance (canal_y,list)) or (isinstance(canal_y, list) and not isinstance (canal_x,list)):
                    raise ValueError('Both X and Y columns must be lists if one is a list.')
                elif (isinstance(canal_x, list) and isinstance(canal_y, list)):
                    if len(canal_x) != len(canal_y):
                        raise ValueError('Multipoint lists must have the same number of row as col')
                    
                    for i in range(len(canal_x)):
                        canal_x_i = canal_x[i]
                        canal_y_i = canal_y[i]
                    
                        ## check values
                        try:
                            canal_x_i = int(canal_x_i)
                            canal_x_i = str(canal_x_i)
                        except:
                            print('Error: X tile must be integer. Skipping.')
                            continue
                        try:
                            canal_y_i = int(canal_y_i)
                            canal_y_i = str(canal_y_i)
                        except:
                            print('Error: Y tile must be integer. Skipping.')
                            continue
                            
                        
                        line = '\tPlaceCanal('+canal_x_i+','+canal_y_i+');\n'
                        canal_code.append(line)
                        
                else:
                    ## check values
                    try:
                        canal_x = int(canal_x)
                        canal_x = str(canal_x)
                    except:
                        print('Error: X tile must be integer. Skipping.')
                        continue
                    try:
                        canal_y = int(canal_y)
                        canal_y = str(canal_y)
                    except:
                        print('Error: Y tile must be integer. Skipping.')
                        continue
                        
                    
                    line = '\tPlaceCanal('+canal_x+','+canal_y+');\n'
                    canal_code.append(line)
        
        
    print('Done.')
        
    return canal_code
    
