pipeline{
    agent{
        docker {
            alwaysPull true
            image 'ts-dockerhub.lsst.org/conda_package_builder:latest'
            args "--entrypoint=''"
        }
    }
    environment {
        user_ci = credentials('lsst-io')
        LTD_USERNAME="${user_ci_USR}"
        LTD_PASSWORD="${user_ci_PSW}"
    }
    stages{
        stage("Build and Upload Documentation"){
            steps{
                sh """
                    source /home/saluser/.setup.sh
                    mamba install -y -c lsstts ts-idl ts-utils ts-salobj ts-scriptqueue ts-observatory-model ts-astrosky-model ts-dateloc ts-observing rubin-sim
                    pip install -e .
                    pip install -r doc/requirements.txt
                    package-docs build
                    pip install ltd-conveyor
                    ltd upload --product ts-scheduler --git-ref ${GIT_BRANCH} --dir doc/_build/html
                """
            }
        }
    }
    post{
       cleanup {
            deleteDir()
        }
    }
}
