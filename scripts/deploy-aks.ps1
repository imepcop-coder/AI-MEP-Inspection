param(
    [string]$ResourceGroup = "rg-monitoring-lab",
    [string]$ClusterName = "aks-monitoring-lab",
    [Parameter(Mandatory = $true)]
    [string]$AcrName,
    [string]$ImageTag = (Get-Date -Format "yyyyMMddHHmmss")
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
    "persistent-volume-claim.yaml",
    "deployment.yaml",
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
$image = "$registryServer/ai-mep-inspection:$ImageTag"
$imageBuild = "ai-mep-inspection:$ImageTag"

Write-Host "Azure subscription: $accountName"
Write-Host "AKS target: $ClusterName (resource group: $ResourceGroup)"
Write-Host "ACR image: $image"
Write-Host "This will build and push an image, update the selected kubeconfig, and apply resources to the AKS cluster."
$confirmation = Read-Host "Type DEPLOY to continue"
if ($confirmation -cne "DEPLOY") {
    Write-Host "Deployment cancelled. No cluster resources were changed."
    return
}

Invoke-CheckedCommand "az" @(
    "acr", "build", "--registry", $AcrName, "--image", $imageBuild, $projectRoot
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
    Invoke-CheckedCommand "kubectl" @(
        "create", "secret", "generic", "ai-mep-secrets",
        "--namespace", "ai-mep",
        "--from-literal=SESSION_SECRET=$sessionSecret",
        "--from-literal=JWT_SECRET=$jwtSecret"
    )
}
else {
    Write-Host "Keeping the existing ai-mep-secrets to preserve the session signing key."
}

foreach ($manifest in @("configmap.yaml", "persistent-volume-claim.yaml", "service.yaml")) {
    Invoke-CheckedCommand "kubectl" @(
        "apply", "--filename", (Join-Path $manifestDirectory $manifest)
    )
}

$deploymentManifest = Join-Path $manifestDirectory "deployment.yaml"
$deploymentText = Get-Content -LiteralPath $deploymentManifest -Raw
$placeholder = "YOUR_ACR_NAME.azurecr.io/ai-mep-inspection:REPLACE_ME"
if (-not $deploymentText.Contains($placeholder)) {
    throw "The deployment manifest image placeholder was not found; refusing to deploy an unexpected image."
}
$deploymentText = $deploymentText.Replace($placeholder, $image)
$temporaryManifest = [System.IO.Path]::GetTempFileName()
try {
    $utf8WithoutBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($temporaryManifest, $deploymentText, $utf8WithoutBom)
    Invoke-CheckedCommand "kubectl" @("apply", "--filename", $temporaryManifest)
}
finally {
    if (Test-Path -LiteralPath $temporaryManifest) {
        Remove-Item -LiteralPath $temporaryManifest -Force
    }
}

Invoke-CheckedCommand "kubectl" @(
    "rollout", "status", "deployment/ai-mep-inspection",
    "--namespace", "ai-mep", "--timeout=300s"
)
Invoke-CheckedCommand "kubectl" @("get", "pods,pvc,services", "--namespace", "ai-mep")

Write-Host ""
Write-Host "Deployment is ready. Open a second PowerShell window and run:"
Write-Host "kubectl port-forward service/ai-mep-inspection 8000:80 --namespace ai-mep"
Write-Host "Then browse to http://127.0.0.1:8000/login"
