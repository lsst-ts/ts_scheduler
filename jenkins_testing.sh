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

conda config --add channels http://conda.lsst.codes/sims
source_eups="source eups-setups.sh"
find_eups=$(${source_eups} 2>&1)
need_install=0
if [ $? != 0 ]; then
	echo "Installing necessary packages"
	need_install=1
	conda install -y lsst-sims-skybrightness
	git clone https://github.com/lsst/sims_skybrightness.git
else
	echo "Updating packages"
	cd ${WORKSPACE}/sims_skybrightness
	git rebase -v
	git fetch -p -t
	cd ${WORKSPACE}
fi
${source_eups}
if [ ${need_install} -eq 1 ]; then
	eups declare sims_skybrightness git -r ${WORKSPACE}/sims_skybrightness -c
fi
setup sims_skybrightness

python -m unittest discover tests
