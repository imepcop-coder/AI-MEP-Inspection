```groovy
@Library('devsecops') _

pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    environment {
        IMAGE_NAME = 'ai-mep-inspection'
        TRIVY = 'C:\\Users\\nk618\\AppData\\Local\\Microsoft\\WinGet\\Packages\\AquaSecurity.Trivy_Microsoft.Winget.Source_8wekyb3d8bbwe\\trivy.exe'
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
                bat '"%TRIVY%" --version'
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

                        withSonarQubeEnv('SonarQube Scanner') {
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

        stage('SCA - Dependency Scan') {
            steps {
                dir('AI-MEP-Inspection') {
                    bat 'python -m pip install pip-audit'
                    bat 'python -m pip_audit -r requirements.txt'
                }
            }
        }

        stage('Docker Build') {
            steps {
                dir('AI-MEP-Inspection') {
                    bat 'docker build -t %IMAGE_NAME%:%BUILD_NUMBER% .'
                    bat 'docker image ls %IMAGE_NAME%'
                }
            }
        }

        stage('Trivy Filesystem Scan') {
            steps {
                dir('AI-MEP-Inspection') {
                    bat '"%TRIVY%" fs --scanners vuln,misconfig --severity HIGH,CRITICAL --exit-code 0 .'
                }
            }
        }

        stage('Trivy Image Scan') {
            steps {
                bat '"%TRIVY%" image --severity HIGH,CRITICAL --exit-code 0 %IMAGE_NAME%:%BUILD_NUMBER%'
            }
        }

        stage('Pipeline Summary') {
            steps {
                echo 'CI pipeline completed successfully'
                echo "Docker image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
            }
        }
    }
}
