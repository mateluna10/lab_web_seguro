pipeline {
    agent any

    environment {
        // Usamos 172.17.0.1 que es la IP del host en la red de Docker en Linux
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
        
        stage('Test - OWASP ZAP Scan') {
            steps {
                // Levantar la app en segundo plano
                sh '''
                    docker run -d --rm --name app_temp -p 5000:5000 $APP_IMAGE
                    sleep 5
                '''
                // Ejecutar OWASP ZAP (Escaneo rápido)
                 sh '''
                    echo "Iniciando escaneo de seguridad con ZAP..."
                    docker run --rm -u root -v $(pwd):/zap/wrk/:rw \
                      ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                      -t $TARGET_URL -r zap-report.html || true
                '''
           
            post {
                always {
                    // Publicar el reporte HTML
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'zap-report.html',
                        reportName: 'Reporte OWASP ZAP'
                    ])
                    // Detener el contenedor temporal
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
