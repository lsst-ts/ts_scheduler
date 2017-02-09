import math
import os
import pkg_resources

__all__ = ["TWOPI", "DEG2RAD", "RAD2DEG", "read_conf_file", "conf_file_path"]

# Routines and non user-specific globals
DEG2RAD = math.pi / 180.    # radians = degrees * DEG2RAD
RAD2DEG = 180. / math.pi    # degrees = radians * RAD2DEG
TWOPI = 2 * math.pi

def read_conf_file(filename):
    """Read the new type of configuration file.

    This function reads the new type of configuration file that contains sections. It also
    has the capability to take parameters as math expressions and lists. String entries in
    list parameters do not need to be surrounded by quotes. An example file is shown below:

    [section]
    # Floating point parameter
    var1 = 1.0
    # String parameter
    var2 = help
    # List of strings parameter
    var3 = [good, to, go]
    # List of floats parameter
    var4 = [1, 2, 4]
    # Boolean parameter
    var5 = True
    # Floating point math expression parameter
    var6 = 375. / 30.
    # Set of tuples
    var7 = (test1, 1.0, 30.0), (test2, 4.0, 50.0)

    Parameters
    ----------
    filename : str
               The configuration file name.

    Returns
    -------
    dict
        A dictionary from the configuration file.
    """
    import ConfigParser as configparser
    config = configparser.SafeConfigParser()
    config.read(filename)

    from collections import defaultdict
    config_dict = defaultdict(dict)
    math_ops = "+,-,*,/".split(',')
    import re
    paren_match = re.compile(r'\(([^\)]+)\)')

    for section in config.sections():
        for key, _ in config.items(section):
            try:
                value = config.getboolean(section, key)
            except ValueError:
                try:
                    value = config.getfloat(section, key)
                except ValueError:
                    value = config.get(section, key)

                    # Handle parameters with math operations
                    check_math = [op for op in math_ops if op in value]
                    if len(check_math):
                        try:
                            value = eval(value)
                        except NameError:
                            pass

                    try:
                        # Handle lists from the configuration
                        if value.startswith('['):
                            value = value.strip('[]')
                            try:
                                value = [float(x) for x in value.split(',')]
                            except ValueError:
                                value = [x.strip() for x in value.split(',')]
                            if len(value) == 1:
                                if value[0] == '':
                                    value = []
                        if value.startswith('('):
                            val_parts = []
                            matches = paren_match.findall(value)
                            for match in matches:
                                parts_list = []
                                parts = match.split(',')
                                for part in parts:
                                    try:
                                        parts_list.append(float(part))
                                    except ValueError:
                                        parts_list.append(part.strip())
                                val_parts.append(tuple(parts_list))
                            value = val_parts
                    except AttributeError:
                        # Above was a float
                        pass

            config_dict[section][key] = value

    return config_dict

def conf_file_path(resource, *paths):
    """Find a configuration file in the package.

    This function uses internal knowledge to determine the correct path of a given
    configuration file.

    Parameters
    ----------
    resource : str
        The name of a module. Usually passed via __name__.
    paths : set of strs
        A variable length set of strings giving the sub-directories and finally the file name.

    Returns
    -------
    str
        The fully qualified path for the given configuration file.
    """
    resource_path = os.path.join(*paths)
    return pkg_resources.resource_filename(resource, resource_path)
