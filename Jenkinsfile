pipeline {
    agent { label 'photohearth-ci' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 25, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '3'))
    }
    triggers { pollSCM('H/5 * * * *') }
    environment {
        CI = 'true'
        PLAYWRIGHT_JUNIT_OUTPUT_FILE = 'reports/browser.xml'
    }
    stages {
        stage('Codigo') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('Dependencias') {
            steps { sh 'uv sync --frozen --python python3.12 && npm ci' }
        }
        stage('Calidad') {
            steps {
                sh '.venv/bin/ruff check backend tests migrations'
                sh 'npm run typecheck && npm run lint'
            }
        }
        stage('API y migraciones') {
            steps { sh '.venv/bin/pytest --junitxml=reports/api.xml' }
        }
        stage('Web y navegadores') {
            steps {
                sh 'npm run build'
                sh 'npm test -- --reporter=line,junit'
            }
        }
        stage('Version desplegable') {
            steps {
                sh 'git archive --format=tar.gz --output=photohearth-source.tar.gz HEAD'
                archiveArtifacts artifacts: 'photohearth-source.tar.gz', fingerprint: true
            }
        }
    }
    post {
        always { junit testResults: 'reports/*.xml', allowEmptyResults: true }
    }
}
