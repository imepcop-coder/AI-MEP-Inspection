
@Library('devsecops') _

pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME = 'ai-mep-inspection'

        ACR_NAME = 'aiminspectionacr'
        ACR_LOGIN_SERVER = 'aiminspectionacr.azurecr.io'

        AZURE_TENANT_ID = '35f26af5-736e-44e6-af08-0adf68c172de'

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
                bat 'where az'
                bat 'az --version'
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

        stage('Publish to Azure Container Registry') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'Azure_devops',
                        usernameVariable: 'AZURE_CLIENT_ID',
                        passwordVariable: 'AZURE_CLIENT_SECRET'
                    )
                ]) {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        try {
                            Write-Host "Step 1: Azure Service Principal Login"

                            az login --service-principal `
                                --username $env:AZURE_CLIENT_ID `
                                --password $env:AZURE_CLIENT_SECRET `
                                --tenant $env:AZURE_TENANT_ID `
                                --output none

                            if ($LASTEXITCODE -ne 0) {
                                throw "Azure authentication failed"
                            }

                            Write-Host "Azure authentication successful"

                            Write-Host "Step 2: ACR Login"

                            az acr login --name $env:ACR_NAME

                            if ($LASTEXITCODE -ne 0) {
                                throw "ACR authentication failed"
                            }

                            Write-Host "ACR authentication successful"

                            $sourceImage = "$($env:IMAGE_NAME):$($env:BUILD_NUMBER)"

                            $targetImage = "$($env:ACR_LOGIN_SERVER)/$($env:IMAGE_NAME):$($env:BUILD_NUMBER)"

                            $latestImage = "$($env:ACR_LOGIN_SERVER)/$($env:IMAGE_NAME):latest"

                            Write-Host "Step 3: Docker Image Tagging"

                            docker tag $sourceImage $targetImage

                            if ($LASTEXITCODE -ne 0) {
                                throw "Docker image tagging failed"
                            }

                            docker tag $sourceImage $latestImage

                            if ($LASTEXITCODE -ne 0) {
                                throw "Latest image tagging failed"
                            }

                            Write-Host "Step 4: Push Versioned Image"

                            docker push $targetImage

                            if ($LASTEXITCODE -ne 0) {
                                throw "Versioned image push failed"
                            }

                            Write-Host "Step 5: Push Latest Image"

                            docker push $latestImage

                            if ($LASTEXITCODE -ne 0) {
                                throw "Latest image push failed"
                            }

                            Write-Host "SUCCESS: Images published to ACR"

                        }
                        finally {
                            az logout 2>$null
                            docker logout $env:ACR_LOGIN_SERVER 2>$null
                        }
                    '''
                }
            }
        }

        stage('Verify ACR Image') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'Azure_devops',
                        usernameVariable: 'AZURE_CLIENT_ID',
                        passwordVariable: 'AZURE_CLIENT_SECRET'
                    )
                ]) {
                    powershell '''
                        $ErrorActionPreference = "Stop"

                        try {
                            az login --service-principal `
                                --username $env:AZURE_CLIENT_ID `
                                --password $env:AZURE_CLIENT_SECRET `
                                --tenant $env:AZURE_TENANT_ID `
                                --output none

                            if ($LASTEXITCODE -ne 0) {
                                throw "Azure login failed during verification"
                            }

                            az acr repository show-tags `
                                --name $env:ACR_NAME `
                                --repository $env:IMAGE_NAME `
                                --output table

                            if ($LASTEXITCODE -ne 0) {
                                throw "ACR repository verification failed"
                            }

                            Write-Host "ACR repository verification completed"

                        }
                        finally {
                            az logout 2>$null
                        }
                    '''
                }
            }
        }

        stage('Pipeline Summary') {
            steps {
                echo 'CI/CD pipeline completed successfully'
                echo "Docker image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
                echo "ACR image: ${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
                echo "Latest image: ${env.ACR_LOGIN_SERVER}/${env.IMAGE_NAME}:latest"
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Build, tests, security scans and ACR publishing completed.'
        }

        failure {
            echo 'FAILURE: Check Jenkins Console Output for the failed stage.'
        }

        always {
            echo 'Pipeline execution finished.'
        }
    }
}
