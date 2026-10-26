# Trial deployment to an existing AKS cluster

This setup is for a trial only. It uses one application replica, SQLite on a
persistent Azure Disk claim, and a private `ClusterIP` service. Do not scale the
deployment above one replica: SQLite and an Azure Disk claim are not a
multi-replica database or shared-file solution.

The app is exposed only through `kubectl port-forward`; this avoids publishing
an HTTP-only trial service to the internet. For production, use a managed
database, shared/object storage for uploads, and an HTTPS ingress before
exposing the app.

## Deploy the trial

The deployment script uses `az acr build`, so a local Docker engine is not
required. It builds a uniquely tagged image, asks for explicit confirmation
before changing Azure/AKS, keeps an existing Kubernetes session secret, applies
the trial manifests, waits for rollout, and prints the pod/service status.

Sign in to the intended Azure subscription first:

```powershell
az login
az account set --subscription "<subscription-name-or-id>"
```

AKS must be authorized to pull images from ACR. If the registry is not already
attached, this command adds the required Azure role assignment:

```powershell
az aks update --resource-group rg-monitoring-lab --name aks-monitoring-lab --attach-acr <acr-name>
```

Then, from the application root, run:

```powershell
.\scripts\deploy-aks.ps1 -AcrName <acr-name>
```

The script defaults to the currently configured trial cluster
`aks-monitoring-lab` in resource group `rg-monitoring-lab`. Override those
parameters if using a different cluster:

```powershell
.\scripts\deploy-aks.ps1 -ResourceGroup <resource-group> -ClusterName <aks-name> -AcrName <acr-name>
```

Review the displayed Azure subscription and cluster before typing `DEPLOY`.
If no ACR with that name is visible in the selected subscription, verify the
subscription or ask an administrator for the correct registry access.

## Open the application

In a separate PowerShell terminal:

```powershell
kubectl port-forward service/ai-mep-inspection 8000:80 --namespace ai-mep
```

Then open <http://127.0.0.1:8000/login>. The app starts with a new empty
database; this trial deployment does not migrate or copy the local SQLite database.
Google sign-in remains unconfigured unless its OAuth settings are separately
provided as Kubernetes Secrets.

## Cleanup

To remove the trial app and its data, delete its namespace:

```powershell
kubectl delete namespace ai-mep
```

This also deletes the SQLite database and files in the app's PVC. Do not run the
cleanup command if you need to preserve trial data.
