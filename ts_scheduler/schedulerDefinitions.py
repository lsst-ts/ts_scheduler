import math
import re

# Routines and non user-specific globals
DEG2RAD = math.pi / 180.    # radians = degrees * DEG2RAD
RAD2DEG = 180. / math.pi    # degrees = radians * RAD2DEG
TWOPI   = 2*math.pi

# Logger level for stdout, higher than Logging.INFO and lower than Logging.WARNING
INFOX = 25

# RE to match a key/value specifier and optional comment - LD (MM modification)
_config_line_re = re.compile(r'^\s*(\w+\[*\w*\]*\s*=\s*[^#]+)(.*)')

# RE to extract key and value - LD (MM modification)
_config_item_re = re.compile(r'^\s*(\w+\[*\w*\]*)\s*=\s*(\S+)')

def readConfFile(fileName):
    """
    Parse the configuration file (fileName) and return a dictionary of
    the content of the file.
    
    fileName must be an ASCII file containing a list of key = value
    pairs, one pair per line. Comments are identified by a '#' and can
    be anywhere in the file. Everything following a '#' (up to the 
    carriage return/new line) is considered to be a comment and 
    ignored.
    
    The dictionary has the form {key: value} where value is a simple 
    number if and only if key appears only one time in fileName. 
    Otherwise, value is an array.
    
    Value can have '=' sign in it: each non-comment line is split 
    using the '=' character as delimiter, only once and starting from 
    the left. Extra white spaces and '\n' characters are stripped from
    both key and value.
    
    An attempt is made to convert value into a float. If that fails, 
    value is assumed to be a string.
    
    
    Input
    fileName:   the name (with path) of the configuration file.
    
    Return
    A dictionary of key = value elements.
    A 2d array of key, value pairs.
    
    Raise
    IOError if fileName cannot be opened for reading.
    """
    conf = {}
    pairs = []
    index = 0

    # Try and read the file fileName (raise IOError if something bad 
    # happens).
    lines = file(fileName).readlines ()
    
    for line in lines:
        line = line.strip()
        if not line:			# skip blank line
            continue
        if line[0]=='#': 		# skip comment line
            continue

        comment = ""
        m = re.search (_config_line_re, line)
        if m:
            good, comment = m.group(1), m.group(2)

        m = re.search (_config_item_re, good)
        if m:
            key, val = m.group(1), m.group(2)

            # store "key = value" string
            pairs.append({
                    'key' : key,
                    'val' : val,
                    'index' : index,
            })
            index += 1

            # Try and convert val to a float
            try:
                val = float (val)
            except:
                # Ops, must be a string, then
                pass
            
            if not conf.has_key (key):
                conf[key] = val
            elif (isinstance (conf[key], list)):
                conf[key].append (val)
            else:
                conf[key] = [conf[key], val]
    return conf, pairs

