pipeline {
    agent any

    environment {
        IMAGE_NAME = "secure-cicd-pipeline:${env.BUILD_NUMBER}"
        // Sibling containers are created by the host Docker daemon (Docker-outside-of-Docker via
        // the mounted socket), which cannot resolve paths inside the Jenkins container's own
        // filesystem (e.g. $WORKSPACE). On Docker Desktop it needs the real host-side path to
        // translate the bind mount correctly, hence HOST_JENKINS_HOME (set in docker-compose.yml).
        HOST_WORKSPACE = "${env.HOST_JENKINS_HOME}/workspace/secure-cicd-pipeline"
    }

    stages {
        stage('Install deps & unit tests') {
            steps {
                sh '''
                    docker run --rm -v "$HOST_WORKSPACE":/src -w /src python:3.11-slim \
                        bash -c "pip install --quiet -r requirements.txt -r requirements-dev.txt && python -m pytest -v"
                '''
            }
        }

        stage('Secrets scan (gitleaks)') {
            steps {
                sh '''
                    docker run --rm -v "$HOST_WORKSPACE":/repo zricethezav/gitleaks:latest detect \
                        --source=/repo --no-git -v \
                        --report-format json --report-path /repo/gitleaks-report.json
                '''
            }
        }

        stage('SAST (semgrep)') {
            steps {
                sh '''
                    docker run --rm -v "$HOST_WORKSPACE":/src returntocorp/semgrep semgrep \
                        --config=p/python --error --json --output /src/semgrep-report.json /src
                '''
            }
        }

        stage('Dependency scan (pip-audit)') {
            steps {
                sh '''
                    docker run --rm -v "$HOST_WORKSPACE":/src -w /src python:3.11-slim \
                        bash -c "pip install --quiet pip-audit && pip-audit -r requirements.txt -f json -o pip-audit-report.json"
                '''
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "$IMAGE_NAME" .'
            }
        }

        stage('Image scan (trivy)') {
            steps {
                sh '''
                    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        -v "$HOST_WORKSPACE":/src aquasec/trivy:latest image \
                        --severity CRITICAL,HIGH --exit-code 1 \
                        --format json --output /src/trivy-report.json \
                        "$IMAGE_NAME"
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '*-report.json', allowEmptyArchive: true
        }
    }
}
