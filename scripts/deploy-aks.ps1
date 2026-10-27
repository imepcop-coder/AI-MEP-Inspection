param(
    [string]$ResourceGroup = "rg-monitoring-lab",
    [string]$ClusterName = "aks-monitoring-lab",
    [Parameter(Mandatory = $true)]
    [string]$AcrName,
    [string]$ImageTag = (Get-Date -Format "yyyyMMddHHmmss"),
    [ValidateSet("development", "production")]
    [string]$AppEnv = "development"
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Executable failed with exit code $LASTEXITCODE."
    }
}

function New-SecretValue {
    $bytes = New-Object byte[] 48
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    }
    finally {
        $random.Dispose()
    }

    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$manifestDirectory = Join-Path $projectRoot "kubernetes"
$requiredManifests = @(
    "namespace.yaml",
    "configmap.yaml",
    "postgres-persistent-volume-claim.yaml",
    "shared-files-persistent-volume-claim.yaml",
    "postgres-service.yaml",
    "postgres-statefulset.yaml",
    "backend-service.yaml",
    "deployment.yaml",
    "frontend-deployment.yaml",
    "service.yaml"
)
foreach ($manifest in $requiredManifests) {
    if (-not (Test-Path (Join-Path $manifestDirectory $manifest))) {
        throw "Required Kubernetes manifest is missing: $manifest"
    }
}

$accountName = & az account show --query name --output tsv
if ($LASTEXITCODE -ne 0 -or -not $accountName) {
    throw "Sign in to Azure first with 'az login' and select the intended subscription."
}

$registryServer = (& az acr show --name $AcrName --query loginServer --output tsv)
if ($LASTEXITCODE -ne 0 -or -not $registryServer) {
    throw "Could not find ACR '$AcrName' in the selected Azure subscription."
}
$backendImage = "$registryServer/ai-mep-inspection:$ImageTag"
$frontendImage = "$registryServer/ai-mep-frontend:$ImageTag"
$backendImageBuild = "ai-mep-inspection:$ImageTag"
$frontendImageBuild = "ai-mep-frontend:$ImageTag"

Write-Host "Azure subscription: $accountName"
Write-Host "AKS target: $ClusterName (resource group: $ResourceGroup)"
Write-Host "Backend image: $backendImage"
Write-Host "Frontend image: $frontendImage"
Write-Host "Application environment: $AppEnv"
Write-Host "This will build and push an image, update the selected kubeconfig, and apply resources to the AKS cluster."
$confirmation = Read-Host "Type DEPLOY to continue"
if ($confirmation -cne "DEPLOY") {
    Write-Host "Deployment cancelled. No cluster resources were changed."
    return
}

Invoke-CheckedCommand "az" @(
    "acr", "build", "--registry", $AcrName, "--image", $backendImageBuild,
    "--file", "Dockerfile", $projectRoot
)
Invoke-CheckedCommand "az" @(
    "acr", "build", "--registry", $AcrName, "--image", $frontendImageBuild,
    "--file", "Dockerfile.frontend", $projectRoot
)
Invoke-CheckedCommand "az" @(
    "aks", "get-credentials", "--resource-group", $ResourceGroup,
    "--name", $ClusterName, "--overwrite-existing"
)

$namespaceManifest = Join-Path $manifestDirectory "namespace.yaml"
Invoke-CheckedCommand "kubectl" @("apply", "--filename", $namespaceManifest)

$existingSecret = & kubectl get secret ai-mep-secrets --namespace ai-mep --ignore-not-found --output name
if ($LASTEXITCODE -ne 0) {
    throw "Could not check for the existing Kubernetes secret."
}
if (-not $existingSecret) {
    $sessionSecret = New-SecretValue
    $jwtSecret = New-SecretValue
    $databaseUser = "ai_mep_app"
    $databasePassword = New-SecretValue
    $databaseUrl = "postgresql+psycopg://$databaseUser`:$databasePassword@ai-mep-postgres:5432/ai_mep"
    Invoke-CheckedCommand "kubectl" @(
        "create", "secret", "generic", "ai-mep-secrets",
        "--namespace", "ai-mep",
        "--from-literal=SESSION_SECRET=$sessionSecret",
        "--from-literal=JWT_SECRET=$jwtSecret",
        "--from-literal=DATABASE_URL=$databaseUrl",
        "--from-literal=POSTGRES_USER=$databaseUser",
        "--from-literal=POSTGRES_PASSWORD=$databasePassword"
    )
}
else {
    $secretPatch = @{}
    foreach ($key in @("SESSION_SECRET", "JWT_SECRET", "DATABASE_URL", "POSTGRES_USER", "POSTGRES_PASSWORD")) {
        $encodedValue = & kubectl get secret ai-mep-secrets --namespace ai-mep --output "jsonpath={.data.$key}"
        if ($LASTEXITCODE -ne 0) {
            throw "Could not read the $key value from the existing ai-mep-secrets."
        }
        if (-not $encodedValue) {
            if ($key -eq "SESSION_SECRET" -or $key -eq "JWT_SECRET") {
                $secretPatch[$key] = New-SecretValue
            }
        }
    }

    $databaseUser = "ai_mep_app"
    $databasePassword = New-SecretValue
    if (-not $secretPatch.ContainsKey("POSTGRES_USER")) {
        $postgresUser = & kubectl get secret ai-mep-secrets --namespace ai-mep --output "jsonpath={.data.POSTGRES_USER}"
        if (-not $postgresUser) {
            $secretPatch["POSTGRES_USER"] = $databaseUser
        }
        else {
            $databaseUser = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($postgresUser))
        }
    }
    $postgresPassword = & kubectl get secret ai-mep-secrets --namespace ai-mep --output "jsonpath={.data.POSTGRES_PASSWORD}"
    if (-not $postgresPassword) {
        $secretPatch["POSTGRES_PASSWORD"] = $databasePassword
    }
    else {
        $databasePassword = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($postgresPassword))
    }
    $databaseUrlValue = & kubectl get secret ai-mep-secrets --namespace ai-mep --output "jsonpath={.data.DATABASE_URL}"
    if ($databaseUrlValue) {
        $existingDatabaseUrl = [System.Text.Encoding]::UTF8.GetString(
            [Convert]::FromBase64String($databaseUrlValue)
        )
        if ($existingDatabaseUrl -notmatch "^postgresql(\+\w+)?://") {
            throw "The existing DATABASE_URL is not PostgreSQL. Migrate the database before deploying multiple backend replicas."
        }
    }
    if (-not $databaseUrlValue) {
        $secretPatch["DATABASE_URL"] = "postgresql+psycopg://$databaseUser`:$databasePassword@ai-mep-postgres:5432/ai_mep"
    }

    if ($secretPatch.Count -gt 0) {
        $patchJson = @{ stringData = $secretPatch } | ConvertTo-Json -Depth 4 -Compress
        Invoke-CheckedCommand "kubectl" @(
            "patch", "secret", "ai-mep-secrets", "--namespace", "ai-mep",
            "--type", "merge", "--patch", $patchJson
        )
    }
    Write-Host "Preserving existing session credentials and completing required database settings."
}

function Apply-ConfigMap {
    $manifestPath = Join-Path $manifestDirectory "configmap.yaml"
    $manifestText = Get-Content -LiteralPath $manifestPath -Raw
    $developmentValue = 'APP_ENV: "development"'
    if (-not $manifestText.Contains($developmentValue)) {
        throw "The APP_ENV placeholder was not found in configmap.yaml."
    }
    $manifestText = $manifestText.Replace($developmentValue, "APP_ENV: `"$AppEnv`"")
    $temporaryManifest = [System.IO.Path]::GetTempFileName()
    try {
        $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($temporaryManifest, $manifestText, $utf8WithoutBom)
        Invoke-CheckedCommand "kubectl" @("apply", "--filename", $temporaryManifest)
    }
    finally {
        if (Test-Path -LiteralPath $temporaryManifest) {
            Remove-Item -LiteralPath $temporaryManifest -Force
        }
    }
}

Apply-ConfigMap

foreach ($manifest in @(
    "postgres-persistent-volume-claim.yaml",
    "shared-files-persistent-volume-claim.yaml",
    "postgres-service.yaml",
    "backend-service.yaml",
    "service.yaml"
)) {
    Invoke-CheckedCommand "kubectl" @(
        "apply", "--filename", (Join-Path $manifestDirectory $manifest)
    )
}

function Apply-ImageManifest {
    param(
        [string]$ManifestName,
        [string]$ImagePlaceholder,
        [string]$Image
    )

    $manifestPath = Join-Path $manifestDirectory $ManifestName
    $manifestText = Get-Content -LiteralPath $manifestPath -Raw
    if (-not $manifestText.Contains($ImagePlaceholder)) {
        throw "The image placeholder was not found in $ManifestName; refusing to deploy an unexpected image."
    }
    $manifestText = $manifestText.Replace($ImagePlaceholder, $Image)
    $temporaryManifest = [System.IO.Path]::GetTempFileName()
    try {
        $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($temporaryManifest, $manifestText, $utf8WithoutBom)
        Invoke-CheckedCommand "kubectl" @("apply", "--filename", $temporaryManifest)
    }
    finally {
        if (Test-Path -LiteralPath $temporaryManifest) {
            Remove-Item -LiteralPath $temporaryManifest -Force
        }
    }
}

Invoke-CheckedCommand "kubectl" @(
    "apply", "--filename", (Join-Path $manifestDirectory "postgres-statefulset.yaml")
)
Invoke-CheckedCommand "kubectl" @(
    "rollout", "status", "statefulset/ai-mep-postgres",
    "--namespace", "ai-mep", "--timeout=300s"
)

Apply-ImageManifest `
    "deployment.yaml" `
    "YOUR_ACR_NAME.azurecr.io/ai-mep-inspection:REPLACE_ME" `
    $backendImage
Apply-ImageManifest `
    "frontend-deployment.yaml" `
    "YOUR_ACR_NAME.azurecr.io/ai-mep-frontend:REPLACE_ME" `
    $frontendImage

Invoke-CheckedCommand "kubectl" @(
    "rollout", "status", "deployment/ai-mep-backend",
    "--namespace", "ai-mep", "--timeout=300s"
)
Invoke-CheckedCommand "kubectl" @(
    "rollout", "status", "deployment/ai-mep-frontend",
    "--namespace", "ai-mep", "--timeout=300s"
)
Invoke-CheckedCommand "kubectl" @(
    "delete", "deployment", "ai-mep-inspection",
    "--namespace", "ai-mep", "--ignore-not-found=true"
)
Invoke-CheckedCommand "kubectl" @("get", "pods,pvc,services", "--namespace", "ai-mep")

Write-Host ""
Write-Host "Deployment is ready. Open a second PowerShell window and run:"
Write-Host "kubectl port-forward service/ai-mep-inspection 8000:80 --namespace ai-mep"
Write-Host "Then browse to http://127.0.0.1:8000/login"
