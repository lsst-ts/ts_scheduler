import os


def load_override_configuration(config, path):
    """A utility method to load the pexConfig override configuration given a path.

    Parameters
    ----------
    config
    path

    Returns
    -------

    """
    config_files = os.listdir(path)

    for ifile in config_files:
        try:
            load_file = os.path.join(path, ifile)
            if not os.path.isdir(load_file):
                config.load(load_file)
        except AssertionError:
            # Not the right configuration file, so do nothing.
            pass


