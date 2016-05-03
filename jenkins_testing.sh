#!/bin/bash
echo "Running LSST Scheduler Jenkins build script"
remote_url=http://lsst-web.ncsa.illinois.edu/~mareuter/sched_stuff

curl -O ${remote_url}/opensplice_libs.tar.gz
tar zxvf opensplice_libs.tar.gz
curl -O ${remote_url}/scheduler_ddslibs.tar.gz
tar zxvf scheduler_ddslibs.tar.gz

echo "Setting paths for Scheduler DDS libraries"
export LD_LIBRARY_PATH=${WORKSPACE}/lib:${LD_LIBRARY_PATH}
export PYTHONPATH=${PYTHONPATH}:${WORKSPACE}/lib

if [ ! -e ${WORKSPACE}/miniconda ]; then
	echo "Setting up Miniconda distribution"    
	curl -O ${remote_url}/Miniconda-latest-Linux-x86_64.sh
	bash Miniconda-latest-Linux-x86_64.sh -b -p miniconda
fi

export PATH=${WORKSPACE}/miniconda/bin:${PATH}

conda config --add channels http://eupsforge.net/conda/dev
conda install -y lsst-sims-skybrightness
pip install -r requirements.txt

source eups-setups.sh
setup sims_skybrightness

python -m unittest discover tests