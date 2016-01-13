import logging
import time
import sys

from observatoryModel import ObservatoryModel

from schedulerDefinitions import INFOX, read_conf_file

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
        model.slew_altazrot(vTime[k], vAlt[k], vAz[k], vRot[k])
        model.start_tracking(vTime[k])
        print model
    sys.exit(0)
