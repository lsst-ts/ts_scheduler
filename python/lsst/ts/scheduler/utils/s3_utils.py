# This file is part of ts_scheduler.
#
# Developed for the Rubin Observatory Telescope and Site Systems.
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

__all__ = ["handle_lfoa"]

from lsst.ts.salobj import AsyncS3Bucket
from lsst.ts.utils import astropy_time_from_tai_unix, current_tai


def handle_lfoa(
    s3bucket_name: str, mock_s3: bool, salname: str, salindexname: int, filename: str
) -> str:
    """Stand alone method to handle sending the large files to S3.

    Parameters
    ----------
    s3bucket_name : `str`
        The name of the S3 bucket to upload the file to.
    mock_s3 : `bool`
        If True, the S3 upload is mocked (useful for testing).
    salname : `str``
        Name of the component.
    salindexname : `int`
        Index of the component.
    filename : `str`
        The path to the local file to be uploaded.

    Returns
    -------
    `str`
        Url of the uploaded file.
    """

    s3bucket = AsyncS3Bucket(name=s3bucket_name, domock=mock_s3, create=mock_s3)

    generator = f"{salname}:{salindexname}"

    key = s3bucket.make_key(
        salname=salname,
        salindexname=salindexname,
        generator=generator,
        date=astropy_time_from_tai_unix(current_tai()),
        suffix=".p",
    )

    with open(filename, "rb") as fileobj:
        s3bucket.bucket.upload_fileobj(Fileobj=fileobj, Key=key)

    url = f"{s3bucket.service_resource.meta.client.meta.endpoint_url}/{s3bucket.name}/{key}"

    return url
