import math
import re

# Routines and non user-specific globals
DEG2RAD = math.pi / 180.    # radians = degrees * DEG2RAD
RAD2DEG = 180. / math.pi    # degrees = radians * RAD2DEG
TWOPI = 2 * math.pi

# Logger level for stdout, higher than Logging.INFO and lower than Logging.WARNING
INFOX = 25

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
    # Floating point math epxression parameter
    var6 = 375. / 30.

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
                        value = eval(value)

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
                    except AttributeError:
                        # Above was a float
                        pass

            config_dict[section][key] = value

    return config_dict
