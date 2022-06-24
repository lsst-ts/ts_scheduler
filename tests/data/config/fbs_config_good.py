import numpy as np

from rubin_sim.scheduler.modelObservatory import Model_observatory
from rubin_sim.scheduler.schedulers import Core_scheduler
from rubin_sim.scheduler.utils import standard_goals, Footprint
import rubin_sim.scheduler.basis_functions as bf
from rubin_sim.scheduler.surveys import Greedy_survey
import rubin_sim.scheduler.detailers as detailers


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
    footprints=None,
    seed=42,
):
    """
    Make a quick set of greedy surveys

    This is a convienence function to generate a list of survey objects that
    can be used with lsst.sims.featureScheduler.schedulers.Core_scheduler.
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
        "survey_name": "greedy",
    }

    surveys = []
    detailer = detailers.Camera_rot_detailer(
        min_rot=np.min(camera_rot_limits), max_rot=np.max(camera_rot_limits)
    )

    for filtername in filters:
        bfs = []
        bfs.append(
            (bf.M5_diff_basis_function(filtername=filtername, nside=nside), m5_weight)
        )
        bfs.append(
            (
                bf.Footprint_basis_function(
                    filtername=filtername,
                    footprint=footprints,
                    out_of_bounds_val=np.nan,
                    nside=nside,
                ),
                footprint_weight,
            )
        )
        bfs.append(
            (
                bf.Slewtime_basis_function(filtername=filtername, nside=nside),
                slewtime_weight,
            )
        )
        bfs.append(
            (bf.Strict_filter_basis_function(filtername=filtername), stayfilter_weight)
        )
        # Masks, give these 0 weight
        bfs.append(
            (
                bf.Zenith_shadow_mask_basis_function(
                    nside=nside, shadow_minutes=shadow_minutes, max_alt=max_alt
                ),
                0,
            )
        )
        bfs.append(
            (
                bf.Moon_avoidance_basis_function(
                    nside=nside, moon_distance=moon_distance
                ),
                0,
            )
        )

        bfs.append((bf.Filter_loaded_basis_function(filternames=filtername), 0))
        bfs.append((bf.Planet_mask_basis_function(nside=nside), 0))

        weights = [val[1] for val in bfs]
        basis_functions = [val[0] for val in bfs]
        surveys.append(
            Greedy_survey(
                basis_functions,
                weights,
                exptime=exptime,
                filtername=filtername,
                nside=nside,
                ignore_obs=ignore_obs,
                nexp=nexp,
                detailers=[detailer],
                **greed_survey_params,
            )
        )

    return surveys


if __name__ == "config":

    nside = 32
    per_night = True  # Dither DDF per night
    seed = 42

    camera_ddf_rot_limit = 75.0

    observatory = Model_observatory(nside=nside, mjd_start=60110.983)
    observatory.sky_model.load_length = 3
    conditions = observatory.return_conditions()

    footprints_hp = standard_goals(nside=nside)

    footprints = Footprint(
        conditions.mjd_start, sun_RA_start=conditions.sun_RA_start, nside=nside
    )
    for i, key in enumerate(footprints_hp):
        footprints.footprints[i, :] = footprints_hp[key]

    greedy = gen_greedy_surveys(nside, nexp=1, footprints=footprints, seed=seed)
    surveys = [greedy]
    scheduler = Core_scheduler(surveys, nside=nside)
