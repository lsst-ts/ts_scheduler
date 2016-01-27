import logging
import time
import sys

from observatoryModel.observatoryModel import ObservatoryModel

from schedulerDefinitions import INFOX, DEG2RAD, read_conf_file

if (__name__ == '__main__'):
    logging.INFOX = INFOX
    logging.addLevelName(logging.INFOX, 'INFOX')

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("scheduler")
    log.setLevel(logging.INFO)

    timestr = time.strftime("%Y-%m-%d_%H:%M:%S")
    logfile = logging.FileHandler("../log/test_observatoryModel.%s.log" % (timestr))
    logfile.setFormatter(formatter)
    logfile.setLevel(logging.INFO)
    log.addHandler(logfile)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    log.addHandler(console)

    model = ObservatoryModel()
    siteConf = read_conf_file("../conf/system/site.conf")
    observatoryConf = read_conf_file("../conf/system/observatoryModel.conf")
    observatoryConf.update(siteConf)

    model.configure(observatoryConf)

    vTime = [0, 100, 200, 300, 400]
    vAlt = [80, 70, 60, 50, 40]
    vAz = [0, 30, 60, 90, 120]
    vRot = [0, 15, 30, 45, 60]

    model.reset()
    print model
    for k in range(len(vTime)):
        model.update_state(vTime[k])
        print model
        model.slew_altazrot(vTime[k], vAlt[k] * DEG2RAD, vAz[k] * DEG2RAD, vRot[k] * DEG2RAD)
        model.start_tracking(vTime[k])
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
