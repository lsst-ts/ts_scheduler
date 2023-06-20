"""Sphinx configuration file for an LSST stack package.
This configuration only affects single-package Sphinx documentation builds.
"""

import lsst.ts.scheduler  # noqa
from documenteer.conf.pipelinespkg import *  # type: ignore # noqa

project = "ts_scheduler"
html_theme_options["logotext"] = project  # type: ignore # noqa
html_title = project
html_short_title = project
doxylink = {}  # Avoid warning: Could not find tag file _doxygen/doxygen.tag

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["ts_scriptqueue"] = ("https://ts-scriptqueue.lsst.io", None)  # type: ignore # noqa
intersphinx_mapping["rubin_sim"] = ("https://rubin-sim.lsst.io", None)  # type: ignore # noqa
