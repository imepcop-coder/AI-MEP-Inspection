from datetime import datetime
import json
import os
import shutil
import traceback
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.ai.provider import analyze_image
from app.auth.tenant import apply_tenant_filter
from app.database.db import get_db
from app.excel.report_generator import create_report
from app.models.document import Document
from app.models.report_template import ReportTemplate

router = APIRouter()

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ------------------------------------------------------------
# Upload Page
# ------------------------------------------------------------
@router.get("/upload")
async def upload_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={}
    )


# ------------------------------------------------------------
# Upload Images
# ------------------------------------------------------------
@router.post("/upload")
async def upload_images(
    request: Request,
    images: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):

    try:

        if not images:
            raise HTTPException(
                status_code=400,
                detail="Please select at least one image."
            )

        results = []

        for image in images:

            if not image.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file."
                )

            safe_name = Path(image.filename).name
            extension = Path(safe_name).suffix.lower()
            stem = Path(safe_name).stem or "upload"

            if extension not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name} is not a supported image."
                )

            if not stem:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file name."
                )

            image.file.seek(0, os.SEEK_END)
            file_size = image.file.tell()
            image.file.seek(0)

            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name} exceeds 10 MB."
                )

            image_bytes = image.file.read()
            if not image_bytes:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is empty."
                )

            try:
                with Image.open(BytesIO(image_bytes)) as image_obj:
                    image_obj.verify()
            except (UnidentifiedImageError, OSError):
                raise HTTPException(
                    status_code=400,
                    detail=f"{safe_name} is not a valid image file."
                )

            image.file.seek(0)
            filename = f"{uuid.uuid4().hex}{extension}"

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            print(f"Saved : {filepath}")

            try:

                ai_response = analyze_image(filepath)

                print(ai_response)

                ai_response = ai_response.strip()

                if ai_response.startswith("```json"):
                    ai_response = ai_response.replace("```json", "")

                if ai_response.startswith("```"):
                    ai_response = ai_response.replace("```", "")

                if ai_response.endswith("```"):
                    ai_response = ai_response[:-3]

                ai_response = ai_response.strip()

                data = json.loads(ai_response)

            except json.JSONDecodeError:

                print("Invalid AI JSON")

                data = {
                    "location": "Unknown",
                    "discipline": "General",
                    "category": "Quality",
                    "severity": "Medium",
                    "snag_description": "AI could not determine a valid construction snag.",
                    "recommendation": "Please inspect the uploaded image manually.",
                    "status": "Open"
                }

            except Exception as ex:

                print(ex)

                data = {
                    "location": "Unknown",
                    "discipline": "General",
                    "category": "Quality",
                    "severity": "Medium",
                    "snag_description": "AI image analysis failed during inspection process.",
                    "recommendation": "Please inspect the uploaded image manually.",
                    "status": "Open"
                }

            data["image"] = filename

            results.append(data)

        user_data = request.session.get("user")
        default_template = apply_tenant_filter(db.query(ReportTemplate), user_data).filter(ReportTemplate.is_default.is_(True)).first()
        report = create_report(results, template=default_template)

        if user_data:
            # Try to read user identifiers from the session. Fall back to None if missing.
            user_id = user_data.get("id") if isinstance(user_data, dict) else None
            company_id = user_data.get("company_id") if isinstance(user_data, dict) else None
            workspace_id = user_data.get("workspace_id") if isinstance(user_data, dict) else None

            document = Document(
                user_id=user_id,
                company_id=company_id,
                workspace_id=workspace_id,
                title="Inspection Report",
                filename=os.path.basename(report),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                document_type="Inspection Report",
                file_size=os.path.getsize(report),
                description=f"Generated from {len(results)} uploaded image(s)",
                uploaded_at=datetime.utcnow(),
            )
            db.add(document)
            db.commit()

        return FileResponse(
            path=report,
            filename="inspection_report.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException:
        raise

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )