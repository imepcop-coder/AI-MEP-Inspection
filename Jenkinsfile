
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
        KIND_CLUSTER = 'devops-lab'
        K8S_NAMESPACE = 'ai-mep'
        DEPLOYMENT_NAME = 'ai-mep-inspection'
        SERVICE_NAME = 'ai-mep-inspection'

        TRIVY = 'C:\\Users\\nk618\\AppData\\Local\\Microsoft\\WinGet\\Packages\\AquaSecurity.Trivy_Microsoft.Winget.Source_8wekyb3d8bbwe\\trivy.exe'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Environment Validation') {
            steps {
                bat 'git --version'
                bat 'python --version'
                bat 'docker --version'
                bat '"%TRIVY%" --version'
                bat 'kubectl version --client'
                bat 'kind version'
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

        stage('SCA Dependency Scan') {
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
                    bat 'docker image inspect %IMAGE_NAME%:%BUILD_NUMBER%'
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

        stage('Validate Kubernetes Cluster') {
            steps {
                bat 'kind get clusters'
                bat 'kubectl config current-context'
                bat 'kubectl get nodes'
            }
        }

        stage('Load Docker Image into kind') {
            steps {
                bat 'kind load docker-image %IMAGE_NAME%:%BUILD_NUMBER% --name %KIND_CLUSTER%'
            }
        }

        stage('Deploy Application') {
            steps {
                powershell '''
                    $ErrorActionPreference = "Stop"

                    kubectl create namespace $env:K8S_NAMESPACE --dry-run=client -o yaml |
                        kubectl apply -f -

                    if ($LASTEXITCODE -ne 0) {
                        throw "Namespace creation failed"
                    }

                    $deployment = "$($env:DEPLOYMENT_NAME)"

                    kubectl create deployment $deployment `
                        --image="$($env:IMAGE_NAME):$($env:BUILD_NUMBER)" `
                        --namespace $env:K8S_NAMESPACE `
                        --dry-run=client -o yaml |
                        kubectl apply -f -

                    if ($LASTEXITCODE -ne 0) {
                        throw "Deployment creation failed"
                    }

                    kubectl set image deployment/$deployment `
                        "$deployment=$($env:IMAGE_NAME):$($env:BUILD_NUMBER)" `
                        -n $env:K8S_NAMESPACE

                    if ($LASTEXITCODE -ne 0) {
                        throw "Image update failed"
                    }

                    kubectl patch deployment $deployment `
                        -n $env:K8S_NAMESPACE `
                        --type=strategic `
                        -p '{"spec":{"template":{"spec":{"containers":[{"name":"ai-mep-inspection","imagePullPolicy":"IfNotPresent"}]}}}}'

                    if ($LASTEXITCODE -ne 0) {
                        throw "Image pull policy update failed"
                    }

                    kubectl rollout status deployment/$deployment `
                        -n $env:K8S_NAMESPACE --timeout=180s

                    if ($LASTEXITCODE -ne 0) {
                        kubectl describe pods -n $env:K8S_NAMESPACE
                        throw "Application rollout failed"
                    }
                '''
            }
        }

        stage('Create Kubernetes Service') {
            steps {
                powershell '''
                    kubectl expose deployment $env:DEPLOYMENT_NAME `
                        --name $env:SERVICE_NAME `
                        --namespace $env:K8S_NAMESPACE `
                        --type ClusterIP `
                        --port 8000 `
                        --target-port 8000 `
                        --dry-run=client -o yaml |
                        kubectl apply -f -

                    if ($LASTEXITCODE -ne 0) {
                        throw "Service creation failed"
                    }
                '''
            }
        }

        stage('Deployment Verification') {
            steps {
                bat 'kubectl get deployments -n %K8S_NAMESPACE%'
                bat 'kubectl get pods -n %K8S_NAMESPACE% -o wide'
                bat 'kubectl get services -n %K8S_NAMESPACE%'
                bat 'kubectl rollout status deployment/%DEPLOYMENT_NAME% -n %K8S_NAMESPACE% --timeout=180s'
            }
        }

        stage('Pipeline Summary') {
            steps {
                echo "Build: ${env.BUILD_NUMBER}"
                echo "Image: ${env.IMAGE_NAME}:${env.BUILD_NUMBER}"
                echo "Cluster: ${env.KIND_CLUSTER}"
                echo "Namespace: ${env.K8S_NAMESPACE}"
                echo 'CI/CD pipeline completed'
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Build, security scans and Kubernetes deployment completed.'
        }

        failure {
            echo 'FAILURE: Inspect the failed stage in Console Output.'
        }

        always {
            echo 'Pipeline execution finished.'
        }
    }
}
