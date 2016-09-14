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
	bash Miniconda-latest-Linux-x86_64.sh -b -p miniconda
fi

export PATH=${WORKSPACE}/miniconda/bin:${PATH}

conda config --add channels http://conda.lsst.codes/sims
source_eups="source eups-setups.sh"
find_eups=$(${source_eups} 2>&1)
if [ $? != 0 ]; then
	echo "Installing necessary packages"
	conda install -y lsst-sims-skybrightness
	pip install -r requirements.txt
else
	echo "Updating packages"
	conda update lsst-sims-skybrightness
fi
${source_eups}
setup sims_skybrightness

python -m unittest discover tests
