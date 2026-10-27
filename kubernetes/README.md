# Scalable AI MEP Inspection deployment

The AKS deployment separates the web edge and application into independent,
replicated workloads:

```text
Browser -> frontend Service -> 2 Nginx frontend pods
                              -> backend Service -> 2 FastAPI backend pods
                                                   -> PostgreSQL StatefulSet
                                                   -> shared Azure Files volume
```

The app renders its pages and handles API requests in FastAPI; Nginx is the
frontend gateway. PostgreSQL is a single persistent database pod, not a
multi-primary database. Backend and frontend replica counts can be changed
independently in their Kubernetes Deployments. Uploaded files and generated
reports use an Azure Files `ReadWriteMany` claim so every backend replica sees
the same files. The old SQLite claim is not deleted or reused.

## Requirements

- An AKS cluster authorized to pull images from an Azure Container Registry.
- The `managed-csi` and `azurefile-csi` StorageClasses.
- Azure CLI, `kubectl`, and PowerShell.

Sign in to the intended subscription and attach ACR if needed:

```powershell
az login
az account set --subscription "<subscription-name-or-id>"
az aks update --resource-group <resource-group> --name <aks-name> --attach-acr <acr-name>
```

## Deploy to AKS

From the application root, run:

```powershell
.\scripts\deploy-aks.ps1 -ResourceGroup <resource-group> -ClusterName <aks-name> -AcrName <acr-name>
```

The script asks for confirmation, builds and pushes both backend and frontend
images, creates the namespace and persistent volumes, provisions PostgreSQL,
and deploys two frontend and two backend replicas. On first deployment it
generates database and session secrets; later runs preserve them. Do not delete
the secret if existing sessions and database access must continue working.

The deployment uses a new PostgreSQL database. It does **not** migrate data
from the previous SQLite database. Existing SQLite files remain on the old
`ai-mep-data` claim; back them up and perform a deliberate migration before
switching any existing installation with data.

Check rollout status:

```powershell
kubectl get deployments,statefulsets,pods,services,pvc --namespace ai-mep
```

For a private trial, forward the frontend service to localhost:

```powershell
kubectl port-forward service/ai-mep-inspection 8000:80 --namespace ai-mep
```

Then open <http://127.0.0.1:8000/login>. The default trial configuration
allows HTTP for this local port-forward. For public access, configure an HTTPS
Ingress and redeploy with `-AppEnv production` so session cookies are secure.
Google sign-in remains optional and needs its own OAuth credentials.

## Local multi-container run

Docker Compose starts PostgreSQL, the app backend, and the Nginx frontend:

```powershell
docker compose up --build --detach
```

Open <http://127.0.0.1:8000/login>. To run two backend containers locally:

```powershell
docker compose up --build --detach --scale backend=2
```

Compose's default credentials are for local development only. Set
`POSTGRES_PASSWORD`, `DATABASE_URL`, `SESSION_SECRET`, and `JWT_SECRET` in the
environment before using Compose anywhere shared or public. Keep the database
URL password URL-encoded (URL-safe generated passwords are easiest).

## Helm

The Helm chart creates the same frontend/backend/PostgreSQL topology and uses
the `azurefile-csi` shared-files claim by default. Create the Kubernetes Secret
`ai-mep-secrets` in the release namespace before installing it. It must contain
`DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SESSION_SECRET`, and
`JWT_SECRET`; the database URL host must match the release's
`<chart-fullname>-postgres` Service. Configure a different
storage class or image repository with a values file when needed.

For example, set secret values in your secure shell environment and create the
Secret before running Helm:

```powershell
kubectl create namespace ai-mep
kubectl create secret generic ai-mep-secrets --namespace ai-mep `
  --from-literal=POSTGRES_USER=$env:POSTGRES_USER `
  --from-literal=POSTGRES_PASSWORD=$env:POSTGRES_PASSWORD `
  --from-literal=DATABASE_URL=$env:DATABASE_URL `
  --from-literal=SESSION_SECRET=$env:SESSION_SECRET `
  --from-literal=JWT_SECRET=$env:JWT_SECRET
helm upgrade --install ai-mep-inspection .\helm\ai-mep-inspection --namespace ai-mep
```

## Cleanup

Deleting the namespace permanently deletes the PostgreSQL data and shared
uploads/reports volumes:

```powershell
kubectl delete namespace ai-mep
```

Take and verify backups before cleanup.
