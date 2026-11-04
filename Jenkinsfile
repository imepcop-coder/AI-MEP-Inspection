@Library('devsecops') _

pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo 'Source code checked out successfully'
            }
        }

        stage('Environment Validation') {
            steps {
                bat 'git --version'
                bat 'python --version'
                bat 'docker --version'
            }
        }

        stage('Secret Detection') {
            steps {
                gitleaksScan([:])
            }
        }

        stage('Unit Testing') {
            steps {
                bat 'python -m pytest -v'
            }
        }

        stage('Pipeline Summary') {
            steps {
                echo 'CI pipeline completed successfully'
            }
        }
    }
}