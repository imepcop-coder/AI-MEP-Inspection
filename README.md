# AI MEP Inspection

AI MEP Inspection is a FastAPI-based engineering inspection workspace with
project tracking, reports, calculators, and AI-assisted inspection workflows.

## Run locally

Docker Compose runs the UI gateway, application backend, and PostgreSQL:

```powershell
docker compose up --build --detach
```

Open <http://127.0.0.1:8000/login>. Compose stores database data, uploads, and
reports in persistent named volumes. For multiple backend containers:

```powershell
docker compose up --build --detach --scale backend=2
```

The default credentials are development-only; set secure database and session
secrets before exposing the app.

## Deploy to Kubernetes

The AKS manifests and deployment instructions are in
[kubernetes/README.md](./kubernetes/README.md). The default deployment uses two
Nginx frontend pods, two FastAPI backend pods, PostgreSQL, and a shared
ReadWriteMany Azure Files volume for uploads and reports. The SQLite database
from an older deployment is not migrated automatically.

The app can also be installed using the Helm chart in
[helm/ai-mep-inspection](./helm/ai-mep-inspection).