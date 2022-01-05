pipeline{
    agent{
        docker {
            alwaysPull true
            image 'ts-dockerhub.lsst.org/conda_package_builder:latest'
            args "-u root --entrypoint=''"
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
                    su - saluser
                    source /home/saluser/.setup.sh
                    conda install -y -c lsstts ts-idl ts-utils ts-salobj ts-scriptqueue ts-observatory-model ts-astrosky-model ts-dateloc rubin-sim
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
       always {
            withEnv(["HOME=${env.WORKSPACE}"]) {
                sh 'chown -R 1003:1003 ${HOME}/'
            }
       }
       cleanup {
            deleteDir()
        }
    }
}
