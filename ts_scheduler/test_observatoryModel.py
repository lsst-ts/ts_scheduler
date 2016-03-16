import logging
import sys

from observatoryModel.observatoryModel import ObservatoryModel

from schedulerDefinitions import DEG2RAD, read_conf_file
from ts_scheduler.setup import configure_logging, create_parser, generate_logfile

if (__name__ == '__main__'):
    parser = create_parser()
    args = parser.parse_args()

    logfilename = generate_logfile("test_observatoryModel")
    configure_logging(args, logfilename)

    logger = logging.getLogger("scheduler")
    logger.info("Configure logFile=%s" % logfilename)

    model = ObservatoryModel()
    siteConf = read_conf_file("../conf/system/site.conf")
    observatoryConf = read_conf_file("../conf/system/observatoryModel.conf")
    observatoryConf.update(siteConf)

    model.configure(observatoryConf)

    vTime = [0, 100, 200, 300, 400, 500, 600, 700, 800]
    vAlt = [80, 70, 60, 50, 40, 30, 45, 67, 85]
    vAz = [0, 30, 60, 90, 120, 180, 260, 300, 0]
    vRot = [0, 15, 30, 45, 60, 85, 120, 150, 180]

    model.reset()
    print model
    for k in range(len(vTime)):
        model.update_state(vTime[k])
        print model
        model.slew_altazrot(vTime[k], vAlt[k] * DEG2RAD, vAz[k] * DEG2RAD, vRot[k] * DEG2RAD)
        model.start_tracking(vTime[k])
        print model

    vTime = [0, 100, 200, 300, 400, 500, 600, 700, 800]
    vRa = [80, 70, 60, 50, 40, 30, 0, -70, -100]
    vDec = [0, -30, -60, -90, 20, 80, 60, 30, 0]
    vAng = [0, 15, 30, 45, 60, 85, 120, 150, 180]

    print
    model.reset()
    print model
    for k in range(len(vTime)):
        model.update_state(vTime[k])
        print model
        model.slew_radecang(vTime[k], vRa[k] * DEG2RAD, vDec[k] * DEG2RAD, vAng[k] * DEG2RAD)
        print model

    vTarget = [0, 90, 180, 360, -90, -180, -360]
    vCurrent = [0, 0, 0, 0, 0, 0, 0]
    for k in range(len(vTarget)):
        print model.get_closest_angle_distance(vTarget[k] * DEG2RAD, vCurrent[k] * DEG2RAD)
    print

    vTarget = [0, 90, 180, 360, -90, -180, -360]
    vCurrent = [0, 0, 0, 0, 0, 0, 0]
    vMin = [-270, -270, -270, -270, -270, -270, -270]
    vMax = [270, 270, 270, 270, 270, 270, 270]
    for k in range(len(vTarget)):
        print model.get_closest_angle_distance(vTarget[k] * DEG2RAD, vCurrent[k] * DEG2RAD,
                                               vMin[k] * DEG2RAD, vMax[k] * DEG2RAD)
    print

    vTarget = [0, 90, 180, 360, -90, -180, -360]
    vCurrent = [180, 180, 180, 180, 180, 180, 180]
    vMin = [-270, -270, -270, -270, -270, -270, -270]
    vMax = [270, 270, 270, 270, 270, 270, 270]
    for k in range(len(vTarget)):
        print model.get_closest_angle_distance(vTarget[k] * DEG2RAD, vCurrent[k] * DEG2RAD,
                                               vMin[k] * DEG2RAD, vMax[k] * DEG2RAD)
    print

    vTarget = [0, 90, 180, 360, -90, -180, -360]
    vCurrent = [-180, -180, -180, -180, -180, -180, -180]
    vMin = [-270, -270, -270, -270, -270, -270, -270]
    vMax = [270, 270, 270, 270, 270, 270, 270]
    for k in range(len(vTarget)):
        print model.get_closest_angle_distance(vTarget[k] * DEG2RAD, vCurrent[k] * DEG2RAD,
                                               vMin[k] * DEG2RAD, vMax[k] * DEG2RAD)
    print

    vTarget = [0, 45, 90, 180, 270, 360, -45, -90, -180, -270, -360]
    vCurrent = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    vMin = [-90, -90, -90, -90, -90, -90, -90, -90, -90, -90, -90]
    vMax = [90, 90, 90, 90, 90, 90, 90, 90, 90, 90, 90]
    for k in range(len(vTarget)):
        print model.get_closest_angle_distance(vTarget[k] * DEG2RAD, vCurrent[k] * DEG2RAD,
                                               vMin[k] * DEG2RAD, vMax[k] * DEG2RAD)

    sys.exit(0)
