'''
This script contains the functions needed to build version.nut for the custom map gamescript
This is based on boiler plate provided by MinimalGS from Leif Linse.
'''


import os

def build_version(outdir, version):
    '''
    This function creates info.nut for a custom map gamescript

    Parameters
    ----------
    outdir : str, path
        Output directory to write the info.nut file.
    version : str
        version of the gamescript.

    Returns
    -------
    None.

    '''
    
    print('Building version.nut...')
    
    ## Input error handling
    if not os.path.isdir(outdir):
        raise ValueError('outdir must be valid directory.')


    ## Open file and begin writing
    version_file = open(os.path.join(outdir,'version.nut'), 'w')
    
    ## Write header comment
    version_file.write('/*\n')
    version_file.write(' * Warning: This file is loaded both by main.nut and info.nut\n')
    version_file.write(" * thus, don't place anything here that is heavy or not required\n")
    version_file.write(' * to be available when OpenTTD scans the info.nut file.\n')
    version_file.write('*/\n\n')
    
    version_file.write('SELF_VERSION <- '+str(version)+';\n')

    
    version_file.close()
    
    print('Done.')