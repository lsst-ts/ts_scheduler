#!/bin/bash
echo "Running LSST Scheduler Jenkins build script"
remote_url=ftp://ftp.noao.edu/pub/lsst/mareuter/sched_stuff

curl -O ${remote_url}/opensplice_libs.tar.gz
tar zxvf opensplice_libs.tar.gz
curl -O ${remote_url}/scheduler_ddslibs.tar.gz
tar zxvf scheduler_ddslibs.tar.gz

echo "Setting paths for Scheduler DDS libraries"
export LD_LIBRARY_PATH=${WORKSPACE}/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=${PYTHONPATH}:${WORKSPACE}/lib

if [ ! -e ${WORKSPACE}/miniconda ]; then
	echo "Setting up Miniconda distribution"    
	curl -O ${remote_url}/Miniconda2-latest-Linux-x86_64.sh
	bash Miniconda2-latest-Linux-x86_64.sh -b -p miniconda
fi

export PATH=${WORKSPACE}/miniconda/bin:${PATH}

need_install=0
conda config --add channels http://conda.lsst.codes/sims
source_eups="source eups-setups.sh"
find_eups=$(${source_eups} 2>&1)
if [ $? != 0 ]; then
	echo "Installing necessary packages"
	conda install -y rubin-scheduler enum34 mock pytest
	conda update astropy
	scheduler-download-data --update
else
	echo "Updating packages"
	conda install rubin-scheduler
	scheduler-download-data --update
fi
${source_eups}

py.test
