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


        stage('SonarQube Analysis') {
            steps {
                dir('AI-MEP-Inspection') {
                    script {
                        def scannerHome = tool 'SonarScanner'
                        withSonarQubeEnv('SonarQube-Local') {
                            bat "\"${scannerHome}\\bin\\sonar-scanner.bat\""
                        }
                    }
                }
            }
        }
        stage('Unit Testing') {
            steps {
                dir('AI-MEP-Inspection') {
                    bat 'python -m pip install -r requirements.txt'
                    bat 'python -m pytest tests/ -v'
                }
            }
        }

        stage('Pipeline Summary') {
            steps {
                echo 'CI pipeline completed successfully'
            }
        }
    }
}

