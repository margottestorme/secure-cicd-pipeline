pipeline {
    agent any

    environment {
        IMAGE_NAME = "secure-cicd-pipeline:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Install deps & unit tests') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE":/src -w /src python:3.11-slim \
                        bash -c "pip install --quiet -r requirements.txt -r requirements-dev.txt && python -m pytest -v"
                '''
            }
        }

        stage('Secrets scan (gitleaks)') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE":/repo zricethezav/gitleaks:latest detect \
                        --source=/repo --no-git -v \
                        --report-format json --report-path /repo/gitleaks-report.json
                '''
            }
        }

        stage('SAST (semgrep)') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE":/src returntocorp/semgrep semgrep \
                        --config=p/python --error --json --output /src/semgrep-report.json /src
                '''
            }
        }

        stage('Dependency scan (pip-audit)') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE":/src -w /src python:3.11-slim \
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
                        -v "$WORKSPACE":/src aquasec/trivy:latest image \
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
