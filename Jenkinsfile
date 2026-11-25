pipeline {
    agent any

    environment {
        TARGET_URL = 'http://172.17.0.1:5000' 
        APP_IMAGE  = 'lab_web_app'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Obteniendo código desde GitHub...'
            }
        }

        stage('Build') {
            steps {
                sh '''
                    echo "Construyendo imagen Docker de la app..."
                    docker build -t $APP_IMAGE .
                '''
            }
        }

        stage('Test - OWASP ZAP Scan') {
            steps {
                sh '''
                    docker run -d --rm --name app_temp -p 5000:5000 $APP_IMAGE
                    sleep 5
                '''
                sh '''
                    echo "Iniciando escaneo de seguridad con ZAP..."
                    docker run --rm -u root -v $(pwd):/zap/wrk/:rw \
                      ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                      -t $TARGET_URL -r zap-report.html || true
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
                    sh 'docker stop app_temp || true'
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    echo "Desplegando en producción (simulado)..."
                    docker stop app_prod || true
                    docker rm app_prod || true
                    docker run -d --name app_prod -p 5000:5000 $APP_IMAGE
                '''
            }
        }
    }
}
