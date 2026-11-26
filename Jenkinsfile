pipeline {
    agent any

    environment {
        APP_IMAGE  = "lab_web_app:${env.BUILD_NUMBER}"
        ZAP_IMAGE  = 'ghcr.io/zaproxy/zaproxy:stable'
        PROD_PORT  = '5001'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log --oneline -3'
            }
        }

        stage('Build') {
            steps {
                sh 'docker build -t $APP_IMAGE .'
                sh 'docker images | grep lab_web_app'
            }
        }

        stage('SCA - pip-audit') {
            steps {
                sh '''
                    docker run --rm -v "$WORKSPACE:/src" -w /src python:3.14-slim \
                      sh -c "pip install --quiet pip-audit && \
                             pip-audit -r requirements.txt -f json -o pip-audit-report.json || true"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'pip-audit-report.json', allowEmptyArchive: true
                }
            }
        }

        stage('Test - OWASP ZAP') {
            steps {
                sh '''
                    docker run -d --rm --name app_temp -p 5000:5000 $APP_IMAGE
                    for i in $(seq 1 30); do
                        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/login | grep -q "200"; then
                            echo "App lista en intento $i"
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs app_temp
                    exit 1
                '''
                sh '''
                    docker run --rm -u root \
                      --add-host=host.docker.internal:host-gateway \
                      -v $(pwd):/zap/wrk/:rw \
                      $ZAP_IMAGE zap-baseline.py \
                      -t http://host.docker.internal:5000 \
                      -r zap-report.html -w zap-warnings.md -J zap-report.json || true
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'zap-report.html',
                        reportName: 'Reporte OWASP ZAP'
                    ])
                    archiveArtifacts artifacts: 'zap-report.html,zap-warnings.md,zap-report.json', allowEmptyArchive: true
                    sh 'docker logs app_temp > app_temp.log 2>&1 || true'
                    archiveArtifacts artifacts: 'app_temp.log', allowEmptyArchive: true
                    sh 'docker stop app_temp 2>/dev/null || true'
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    docker stop app_prod 2>/dev/null || true
                    docker rm   app_prod 2>/dev/null || true
                    docker run -d --name app_prod -p $PROD_PORT:5000 $APP_IMAGE
                    echo "Produccion simulada en http://localhost:$PROD_PORT"
                '''
            }
        }
    }

    post {
        always {
            echo "Build ${env.BUILD_NUMBER}: ${currentBuild.currentResult}"
        }
    }
}
