@Library('devsecops') _

pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Secret Detection') {
            steps {
                gitleaksScan()
            }
        }

        stage('Unit Testing') {
            steps {
                bat 'python -m pytest -v'
            }
        }
    }
}