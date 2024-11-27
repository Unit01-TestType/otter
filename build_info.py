'''
This script contains the functions needed to build info.nut for the custom map gamescript
This is based on boiler plate provided by MinimalGS from Leif Linse.
'''


import os

def build_info(outdir, author, name, short_name, description, version='SELF_VERSION', date='', API_version='1.11', url='', comment=''):
    '''
    This function creates info.nut for a custom map gamescript

    Parameters
    ----------
    outdir : str, path
        Output directory to write the info.nut file.
    author : str
        Author of the gamescript.
    name : str
        Name of the gamescript.
    short_name : str
        Short name of the gamescript, must be four letters.
    description : str
        Brief description of the gamescript.
    version : str, optional
        The gamescript version. The default is 'SELF_VERSION' to get from version.nut.
    date : str, optional
        The date of the gamescript version. The default is ''.
    API_version : str, optional
        The API version to use for the gamescript. The default is '1.11'.
    url : str, optional
        URL to more informatoin for the gamescript or the author. The default is ''.
    comment : str, optional
        Header block comment to include at the top of info.nut with formatting. The default is ''.

    Returns
    -------
    None.

    '''
    
    ## Input error handling
    if not os.path.isdir(outdir):
        raise Exception('outdir must be valid directory.')
        
    if not isinstance(author,str):
        raise ValueError('author must be string')
    if not isinstance(name,str):
        raise ValueError('name must be string')
    if not isinstance(short_name,str):
        raise ValueError('short_name must be string')
    if not isinstance(description,str):
        raise ValueError('description must be string')        
    if not isinstance(date,str):
        raise ValueError('date must be string')        
    if not isinstance(API_version,str):
        raise ValueError('API_version must be string')
    if not isinstance(url,str):
        raise ValueError('url must be string')
        
    if len(short_name) != 4:
        raise ValueError('short_name must only be 4 letters')
    

    ## Open file and begin writing
    info_file = open(os.path.join(outdir,'info.nut'), 'w')
    
    ## Write header comment
    info_file.write('/*\n')
    comment = comment.replace('\n','\n * ')
    info_file.write(' * '+comment+'\n')
    info_file.write('*/\n\n')
    
    info_file.write('requre("version.nut")\n\n')
    
    ## Write GSInfo extension class with input parameters
    info_file.write('class FMainClass extends GSInfo {\n')
    info_file.write('\tfunction GetAuthor()\t\t{ return '+'"'+author+'"'+'; }\n')
    info_file.write('\tfunction GetName()\t\t\t{ return '+'"'+name+'"'+'; }\n')
    info_file.write('\tfunction GetDescription() \t{ return '+'"'+description+'"'+'; }\n')
    info_file.write('\tfunction GetVersion()\t\t{ return '+version+'; }\n')
    info_file.write('\tfunction GetDate()\t\t\t{ return '+'"'+date+'"'+'; }\n')
    info_file.write('\tfunction CreateInstance()\t{ return '+'"MainClass"; }\n')
    info_file.write('\tfunction GetShortName() \t{ return '+'"'+short_name+'"'+'; }\n')
    info_file.write('\tfunction GetAPIVersion() \t{ return '+'"'+API_version+'"'+'; }\n')
    info_file.write('\tfunction getURL() \t{ return '+'"'+url+'"'+'; }\n')
    
    ## write settings function
    info_file.write('\tfunction GetSettingsO() {\n')
    info_file.write('\t\tAddSettings({name = "log_level", description = "Debug: Log level (higher = print more)", easy_value = 3, medium_value = 3, hard_value = 3, custom_value = 3, flags = CONFIG_INGAME, min_value = 1, max_value = 3});\n')
    info_file.write('\t\tAddLabels("log_level", {_1 = "1: Info", _2 = "2: Verbose", _3 = "3: Debug" } );\n')
    info_file.write('\t}\n')
    info_file.write('}\n\n')
    
    info_file.write('RegisterGS(FMainClass());\n')
    
    info_file.close()
    
    
    
# build_info(outdir = r'C:\Users\Marc\Documents\OpenTTD\game\CA-townplacer2',
#            author = 'test_author',
#            name = 'test_name',
#            short_name = 'TEST',
#            description = 'test description',
#            version = 'SELF_VERSION',
#            date = '01-01-2024',
#            API_version='1.11',
#            url = 'test_url',
#            comment = 'This is a test comment.\nThis is the second line.\nThis is the third line.\n')
    
    