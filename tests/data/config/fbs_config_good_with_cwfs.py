import numpy as np
import rubin_scheduler.scheduler.basis_functions as bf
import rubin_scheduler.scheduler.detailers as detailers
from rubin_scheduler.scheduler.model_observatory import ModelObservatory
from rubin_scheduler.scheduler.schedulers import CoreScheduler
from rubin_scheduler.scheduler.surveys import GreedySurvey
from rubin_scheduler.scheduler.utils import Footprint, SkyAreaGenerator
from rubin_scheduler.utils import SURVEY_START_MJD as MJD_START


def gen_cwfs_survey(nside, survey_name, science_program, time_gap_min):
    bfs = [
        bf.SlewtimeBasisFunction(nside=nside),
        bf.MoonAvoidanceBasisFunction(nside=nside),
        bf.AltAzShadowMaskBasisFunction(min_alt=28.0, max_alt=85.5, nside=nside),
        bf.VisitGap(note=survey_name, gap_min=time_gap_min),
    ]

    survey_detailers = [
        detailers.TrackingInfoDetailer(
            science_program=science_program,
        ),
    ]
    return [
        GreedySurvey(
            bfs,
            np.ones_like(bfs) * 1000.0,
            nside=nside,
            survey_name=survey_name,
            detailers=survey_detailers,
            nexp=4,
        )
    ]


def gen_greedy_surveys(
    nside=32,
    nexp=1,
    exptime=30.0,
    filters=["r", "i", "z", "y"],
    camera_rot_limits=[-80.0, 80.0],
    shadow_minutes=60.0,
    max_alt=76.0,
    moon_distance=30.0,
    ignore_obs="DD",
    m5_weight=3.0,
    footprint_weight=0.3,
    slewtime_weight=3.0,
    stayfilter_weight=3.0,
    sun_alt_limit=-18,
    footprints=None,
    seed=42,
):
    """
    Make a quick set of greedy surveys

    This is a convenience function to generate a list of survey objects that
    can be used with lsst.sims.featureScheduler.schedulers.CoreScheduler.
    To ensure we are robust against changes in the sims_featureScheduler
    codebase, all kwargs are explicitly set.

    Parameters
    ----------
    nside : int (32)
        The HEALpix nside to use.
    nexp : int (1)
        The number of exposures to use in a visit.
    exptime : float (30.)
        The exposure time to use per visit (seconds).
    filters : list of str (['r', 'i', 'z', 'y'])
        Which filters to generate surveys for.
    camera_rot_limits : list of float ([-80., 80.])
        The limits to impose when rotationally dithering the camera (degrees).
    shadow_minutes : float (60.)
        Used to mask regions around zenith (minutes).
    max_alt : float (76.)
        The maximium altitude to use when masking zenith (degrees).
    moon_distance : float (30.)
        The mask radius to apply around the moon (degrees).
    ignore_obs : str or list of str ('DD')
        Ignore observations by surveys that include the given substring(s).
    m5_weight : float (3.)
        The weight for the 5-sigma depth difference basis function.
    footprint_weight : float (0.3)
        The weight on the survey footprint basis function.
    slewtime_weight : float (3.)
        The weight on the slewtime basis function.
    stayfilter_weight : float (3.)
        The weight on basis function that tries to stay avoid filter changes.
    seed : int (42)
        The random generator seed.
    """
    # Define the extra parameters that are used in the greedy survey. I
    # think these are fairly set, so no need to promote to utility func kwargs
    greed_survey_params = {
        "block_size": 1,
        "smoothing_kernel": None,
        "seed": seed,
        "camera": "LSST",
        "dither": True,
        "survey_name": "Greedy",
    }

    surveys = []
    survey_detailers = [
        detailers.CameraRotDetailer(
            min_rot=np.min(camera_rot_limits), max_rot=np.max(camera_rot_limits)
        ),
        detailers.TrackingInfoDetailer(
            science_program="BLOCK-2",
        ),
    ]

    for filtername in filters:
        bfs = [
            (bf.M5DiffBasisFunction(filtername=filtername, nside=nside), m5_weight),
            (
                bf.FootprintBasisFunction(
                    filtername=filtername,
                    footprint=footprints,
                    out_of_bounds_val=np.nan,
                    nside=nside,
                ),
                footprint_weight,
            ),
            (
                bf.SlewtimeBasisFunction(filtername=filtername, nside=nside),
                slewtime_weight,
            ),
            (bf.StrictFilterBasisFunction(filtername=filtername), stayfilter_weight),
            (bf.NotTwilightBasisFunction(sun_alt_limit=sun_alt_limit), 0),
            # Masks, give these 0 weight
            (
                bf.AltAzShadowMaskBasisFunction(
                    nside=nside, shadow_minutes=shadow_minutes, max_alt=max_alt
                ),
                0,
            ),
            (
                bf.MoonAvoidanceBasisFunction(nside=nside, moon_distance=moon_distance),
                0,
            ),
            (bf.FilterLoadedBasisFunction(filternames=filtername), 0),
            (bf.PlanetMaskBasisFunction(nside=nside), 0),
        ]

        weights = [val[1] for val in bfs]
        basis_functions = [val[0] for val in bfs]
        surveys.append(
            GreedySurvey(
                basis_functions,
                weights,
                exptime=exptime,
                filtername=filtername,
                nside=nside,
                ignore_obs=ignore_obs,
                nexp=nexp,
                detailers=survey_detailers,
                **greed_survey_params,
            )
        )

    return surveys


if __name__ == "config":
    nside = 32
    per_night = True  # Dither DDF per night
    seed = 42

    camera_ddf_rot_limit = 75.0

    observatory = ModelObservatory(nside=nside, mjd_start=MJD_START)
    observatory.sky_model.load_length = 3
    conditions = observatory.return_conditions()

    sky = SkyAreaGenerator(nside=nside)
    footprints_hp, labels = sky.return_maps()

    footprints = Footprint(MJD_START, sun_ra_start=conditions.sun_ra, nside=nside)
    for i, key in enumerate(footprints_hp.dtype.names):
        footprints.footprints[i, :] = footprints_hp[key]

    greedy = gen_greedy_surveys(nside, nexp=1, footprints=footprints, seed=seed)
    cwfs = gen_cwfs_survey(
        nside=nside,
        survey_name="CurvatureWavefrontSensing",
        science_program="BLOCK-1",
        time_gap_min=5.0,
    )

    surveys = [cwfs, greedy]

    scheduler = CoreScheduler(surveys, nside=nside)
