# This file is part of ts_scheduler
#
# Developed for the Vera Rubin Observatory Telescope and Site Systems.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import pathlib
import subprocess
import typing
from unittest.mock import patch

import numpy as np
import pytest
import requests
from lsst.ts import utils
from lsst.ts.scheduler.utils import efd_utils
from rubin_scheduler.data.data_sets import get_data_dir
from rubin_scheduler.data.rs_download_sky import MyHTMLParser

DDS_VERSION = True

try:
    from lsst.ts.salobj import parse_idl  # noqa: F401
except ImportError:
    DDS_VERSION = False


def has_required_sky_file(path: pathlib.Path, mjd: float) -> bool:
    """Check if path contains required sky brightness file for input mjd.

    Parameters
    ----------
    path : `pathlib.Path`
        Path of the sky brightness files.
    mjd : `float`
        MJD of the test.

    Returns
    -------
    `bool`
        `True` is skybrightnees file for inut mjd exists, `False` otherwise.
    """
    sky_brightness_files = [f.name for f in path.glob("*.h5")]

    sky_brightness_dates_range = parse_dates_range(
        sky_brightness_files=sky_brightness_files
    )

    if len(sky_brightness_dates_range) == 0:
        return False

    for mjd_min, mjd_max in sky_brightness_dates_range:
        if mjd_min < mjd < mjd_max:
            return True

    return False


def parse_dates_range(
    sky_brightness_files: typing.List[str],
) -> typing.List[typing.Tuple[float, float]]:
    """Parse sky brightness files names into dates range.

    Parameters
    ----------
    sky_brightness_files : `typing.List[str]`
        List of sky brightness files names.

    Returns
    -------
    sky_brightness_dates_range : `typing.List[typing.Tuple[float, float]]`
        List of dates range (in mjd).
    """
    sky_brightness_dates_range = [
        tuple(
            np.array(f.rsplit(".", maxsplit=1)[0].split("_", maxsplit=1), dtype=float)
        )
        for f in sky_brightness_files
    ]

    return sky_brightness_dates_range


def find_sky_file(source: str, mjd: float) -> str:
    """Find sky file in source for a given mjd.

    Parameters
    ----------
    source : `str`
        Source of sky files.
    mjd : `float`
        Required MJD.

    Returns
    -------
    `str`
        Remote source file.
    """

    source_html_content = requests.get(source)

    parser = MyHTMLParser()

    parser.feed(source_html_content.text)
    parser.close()

    sky_files = parser.filenames

    sky_brightness_dates_range = parse_dates_range(sky_files)

    for mjd_min, mjd_max in sky_brightness_dates_range:
        if mjd_min < mjd < mjd_max:
            return f"{mjd_min:.0f}_{mjd_max:.0f}.h5"

    raise RuntimeError(
        f"No suitable sky brightness file found for mjd={mjd} in {source}. "
        f"Available files are: { ', '.join(sky_files)}."
    )


def download_sky_file(path: pathlib.Path, mjd: float) -> None:
    """Download sky file for the specified mjd into the provided path from the
    rubin_sim_data server.

    Parameters
    ----------
    path : `pathlib.Path`
        Path of the sky brightness files.
    mjd : `float`
        MJD of the test.
    """
    source = "https://s3df.slac.stanford.edu/groups/rubin/static/sim-data/"
    source += "sims_skybrightness_pre/h5_2023_09_12/"

    if not path.exists():
        path.mkdir(parents=True)

    sky_file = find_sky_file(source, mjd)

    sky_file_path = path / sky_file

    print(
        f"Downloading sky brightness file {source + sky_file} -> {sky_file_path.as_posix()}"
    )

    sky_file_content = requests.get(source + sky_file)

    with open(sky_file_path.as_posix(), "wb") as f:
        f.write(sky_file_content.content)


@pytest.fixture(scope="session", autouse=True)
def get_skybrightness_data() -> None:
    """Download sky brightness file required to run the test."""

    mjd = utils.astropy_time_from_tai_unix(utils.current_tai()).mjd

    sky_brightness_data_dir = pathlib.Path(get_data_dir()) / "skybrightness_pre"

    if not has_required_sky_file(sky_brightness_data_dir, mjd):
        # Download file
        download_sky_file(sky_brightness_data_dir, mjd)


@pytest.fixture(scope="session", autouse=True)
def start_ospl_daemon() -> None:
    """Start ospl daemon."""

    if not DDS_VERSION:
        print("Running non-dds version.")
        yield
        return

    # Check if a daemon is already running
    output = subprocess.run(["ospl", "status", "-e"])

    if output.returncode > 2:
        print("ospl daemon not running, starting with local no-network config.")

        # daemon is not running, select local no-network ospl config to start
        # process.
        ospl_config = pathlib.Path(
            "./tests/data/ospl/ospl-shmem-debug-no-network.xml"
        ).resolve()

        old_ospl_config = os.environ["OSPL_URI"]

        os.environ["OSPL_URI"] = ospl_config.as_uri()
        subprocess.run(["ospl", "start"])

        yield

        subprocess.run(["ospl", "stop"])
        os.environ["OSPL_URI"] = old_ospl_config
    else:
        print(f"ospl status {output.returncode}... Nothing to do.")

        yield


@pytest.fixture(scope="session", autouse=True)
def mock_efd_client() -> None:
    efd_utils.__with_lsst_efd_client__ = False


@pytest.fixture(autouse=True)
def patch_environment(monkeypatch):
    monkeypatch.setenv("IMAGE_SERVER_URL", "mytemp")


@pytest.fixture(autouse=True)
def patch_get_next_obs_id():
    with patch("lsst.ts.utils.ImageNameServiceClient.get_next_obs_id") as mock_method:
        # Configure the mock if needed, e.g., set return_value
        mock_method.return_value = (0, "BL1_O_20240906_000001")
        yield mock_method
