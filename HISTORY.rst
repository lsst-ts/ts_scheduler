.. :changelog:

History
-------

====================
0.2   (2015-12-23)
--------------------

Observatory Model states and tracking implemented.
Generic basic Proposal implemented.
First version of scripted proposal implemented.
Fields table read from configuration file.
Configuration from external SOCS.
Transmission of fields.


====================
0.1.4 (2015-10-22)
--------------------

LSS_DDS_DOMAIN handling
logger extended to stdout for INFO+ level

#	deleted:    ts_scheduler/build_scheduler
    unused copy
#	deleted:    ts_scheduler/dev_setup.env
    replaced by scheduler.env

#	new file:   ts_scheduler/schedulerDefinitions.py
    logger INFOX level definition

#	modified:   ts_scheduler/scheduler.env
    LSST_DDS_DOMAIN variable added
#	modified:   ts_scheduler/schedulerMain.py
    logger extended to stdout when level appropriate

====================
0.1.3 (2015-10-21)
--------------------
* Cookiecutter compliant

====================
0.1.2 (2015-10-14)
--------------------
* Logger

====================
0.1.1 (2015-10-09)
--------------------
* Interface tests

+ scheduler.py
+ schedulerMain.py
+ schedulerDriver.py
+ schedulerTarget.py
+ schedulerTest.py
+ build_scheduler

====================
0.1.0 (2015-08-31)
--------------------
* First release on ts_scheduler repository.
