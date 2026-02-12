@Library('JenkinsShared')_
DevelopPipeline(
    name: "ts_scheduler",
    module_name: "lsst.ts.scheduler",
    extra_packages: ["lsst-ts/ts_observatory_model", "lsst-ts/ts_astrosky_model", "lsst-ts/ts_dateloc", "lsst-ts/ts_observing", "lsst-ts/ts_config_scheduler"],
    build_all_idl: true,
    mount_rubin_sim_data: true,
)
