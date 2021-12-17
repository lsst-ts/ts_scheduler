"""Sphinx configuration file for an LSST stack package.
This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.conf.pipelinespkg import *
import lsst.ts.scheduler

project = "ts_scheduler"
html_theme_options["logotext"] = project
html_title = project
html_short_title = project
doxylink = {}  # Avoid warning: Could not find tag file _doxygen/doxygen.tag

intersphinx_mapping["ts_xml"] = ("https://ts-xml.lsst.io", None)
intersphinx_mapping["ts_salobj"] = ("https://ts-salobj.lsst.io", None)
intersphinx_mapping["ts_scriptqueue"] = ("https://ts-scriptqueue.lsst.io", None)
intersphinx_mapping["rubin_sim"] = ("https://rubin-sim.lsst.io", None)
