import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
import asyncio
import json as _json
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.ai.prompts import DISCIPLINE_PROMPTS, DOCUMENT_PROMPTS
from app.ai.provider import AIUnavailable, analyze_image, generate_text
from app.auth.tenant import apply_tenant_filter, get_authenticated_user
from app.database.db import get_db
from app.models.ai_request import AIRequest
from app.models.chat import Chat, ChatMessage
from app.models.user import User

router = APIRouter()
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _get_authenticated_user(request: Request, db: Session):
    return get_authenticated_user(request, db)


# ============================================================
# Chat Management
# ============================================================
@router.get("/assistant")
async def assistant_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = _get_authenticated_user(request, db)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse(url="/login", status_code=303)
        raise

    chats = apply_tenant_filter(db.query(Chat), user).order_by(Chat.updated_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="assistant.html",
        context={
            "user": user,
            "chats": chats,
            "document_types": list(DOCUMENT_PROMPTS.keys()),
            "disciplines": list(DISCIPLINE_PROMPTS.keys()),
        },
    )


@router.post("/api/chats")
async def create_chat(request: Request, db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    body = await request.json()
    title = body.get("title", "New Chat")
    document_type = body.get("document_type", "General")

    chat = Chat(user_id=user.id, company_id=user.company_id, workspace_id=user.workspace_id, title=title, document_type=document_type)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return JSONResponse(
        content={
            "id": chat.id,
            "title": chat.title,
            "document_type": chat.document_type,
            "created_at": chat.created_at.isoformat(),
        }
    )


@router.get("/api/chats")
async def list_chats(request: Request, db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    chats = apply_tenant_filter(db.query(Chat), user).order_by(Chat.updated_at.desc()).all()

    return JSONResponse(
        content=[
            {
                "id": chat.id,
                "title": chat.title,
                "document_type": chat.document_type,
                "updated_at": chat.updated_at.isoformat(),
                "message_count": len(chat.messages),
            }
            for chat in chats
        ]
    )


@router.put("/api/chats/{chat_id}")
async def update_chat(chat_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    body = await request.json()
    if "title" in body:
        chat.title = body["title"]
    if "document_type" in body:
        chat.document_type = body["document_type"]

    chat.updated_at = datetime.utcnow()
    db.commit()

    return JSONResponse(content={"id": chat.id, "title": chat.title})


@router.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(chat)
    db.commit()

    return JSONResponse(content={"status": "deleted"})


# ============================================================
# Messages
# ============================================================
@router.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()

    return JSONResponse(
        content=[
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
    )


@router.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: int, request: Request, db: Session = Depends(get_db)):
    # Keep legacy non-streaming endpoint for compatibility
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    document_type = body.get("document_type", chat.document_type)
    discipline = body.get("discipline")

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    user_msg = ChatMessage(chat_id=chat_id, role="user", content=prompt)
    db.add(user_msg)
    db.commit()

    doc_prompt = DOCUMENT_PROMPTS.get(document_type, {})
    system_prompt = doc_prompt.get("system", "You are a helpful engineering assistant.")

    if discipline and discipline in DISCIPLINE_PROMPTS:
        system_prompt += f" {DISCIPLINE_PROMPTS[discipline]}"

    try:
        answer = generate_text(prompt, system_prompt)

        ai_msg = ChatMessage(chat_id=chat_id, role="assistant", content=answer)
        db.add(ai_msg)

        ai_req = AIRequest(
            user_id=user.id,
            company_id=user.company_id,
            workspace_id=user.workspace_id,
            request_type="assistant_chat",
            prompt=prompt,
            response=answer,
        )
        db.add(ai_req)

        if len(chat.messages) == 1:
            title_prompt = prompt[:50]
            if len(prompt) > 50:
                title_prompt += "..."
            chat.title = title_prompt
            chat.document_type = document_type

        chat.updated_at = datetime.utcnow()
        db.commit()

        return JSONResponse(
            content={
                "id": ai_msg.id,
                "role": "assistant",
                "content": answer,
                "created_at": ai_msg.created_at.isoformat(),
            }
        )

    except Exception as exc:
        error_response = f"Error generating response: {str(exc)}"
        ai_msg = ChatMessage(chat_id=chat_id, role="assistant", content=error_response)
        db.add(ai_msg)
        db.commit()

        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/chats/{chat_id}/stream")
async def stream_message(chat_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Streams generated assistant text as a plain text stream. The client reads the response body progressively.
    """
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    document_type = body.get("document_type", chat.document_type)
    discipline = body.get("discipline")

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    # Save user message immediately
    user_msg = ChatMessage(chat_id=chat_id, role="user", content=prompt)
    db.add(user_msg)
    db.commit()

    # Placeholder assistant message (will be updated when generation completes)
    ai_msg = ChatMessage(chat_id=chat_id, role="assistant", content="")
    db.add(ai_msg)
    db.commit()

    doc_prompt = DOCUMENT_PROMPTS.get(document_type, {})
    system_prompt = doc_prompt.get("system", "You are a helpful engineering assistant.")
    if discipline and discipline in DISCIPLINE_PROMPTS:
        system_prompt += f" {DISCIPLINE_PROMPTS[discipline]}"

    queue: asyncio.Queue = asyncio.Queue()

    async def stream_generator():
        # start with a tiny heartbeat so client sees connection quickly
        yield ("\n").encode()
        while True:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                # heartbeat to keep connection alive
                yield ("\n").encode()
                continue

            if chunk is None:
                break

            if isinstance(chunk, str):
                yield chunk.encode('utf-8')
            else:
                yield chunk

        # end
        return

    loop = asyncio.get_event_loop()

    async def produce():
        try:
            # Run generator in thread to avoid blocking event loop
            def call_gen():
                return generate_text(prompt, system_prompt)

            text = await loop.run_in_executor(None, call_gen)

            # split into chunks
            chunk_size = 256
            for i in range(0, len(text), chunk_size):
                await queue.put(text[i : i + chunk_size])
            # final newline
            await queue.put("\n")

            # persist final assistant message and AIRequest
            ai_msg.content = text
            ai_req = AIRequest(
                user_id=user.id,
                company_id=user.company_id,
                workspace_id=user.workspace_id,
                request_type="assistant_chat",
                prompt=prompt,
                response=text,
            )
            db.add(ai_req)

            if len(chat.messages) == 1:
                title_prompt = prompt[:50]
                if len(prompt) > 50:
                    title_prompt += "..."
                chat.title = title_prompt
                chat.document_type = document_type

            chat.updated_at = datetime.utcnow()
            db.commit()
        except Exception as exc:
            # Push friendly error message
            err_text = 'AI service is temporarily unavailable. You can retry or continue working while we reconnect.'
            try:
                await queue.put(err_text)
            except Exception:
                pass
            # ensure DB records the error response
            ai_msg.content = err_text
            db.add(ai_msg)
            db.commit()
        finally:
            await queue.put(None)

    # start background producer
    asyncio.create_task(produce())

    return StreamingResponse(stream_generator(), media_type='text/plain; charset=utf-8')


# ============================================================
# File Upload & Analysis
# ============================================================
@router.post("/api/chats/{chat_id}/upload")
async def upload_file(chat_id: int, request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = _get_authenticated_user(request, db)

    chat = apply_tenant_filter(db.query(Chat), user).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    upload_dir = "uploads/chat_files"
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{chat_id}_{datetime.utcnow().timestamp()}_{file.filename}"
    filepath = os.path.join(upload_dir, filename)

    with open(filepath, "wb") as handle:
        content = await file.read()
        handle.write(content)

    prompt = f"Please analyze and summarize the following file: {file.filename}. Extract key findings, issues, and recommendations."

    user_msg = ChatMessage(chat_id=chat_id, role="user", content=f"📎 Uploaded: {file.filename}\n\n{prompt}")
    db.add(user_msg)
    db.commit()

    try:
        extension = os.path.splitext(file.filename)[1].lower()
        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            ai_payload = analyze_image(filepath)
            try:
                payload = json.loads(ai_payload)
                if isinstance(payload, dict):
                    issue = payload.get("snag_description") or "No issue identified"
                    recommendation = payload.get("recommendation") or "Review the item manually"
                    answer = (
                        f"Image analysis completed.\n\n"
                        f"Discipline: {payload.get('discipline', 'General')}\n"
                        f"Severity: {payload.get('severity', 'Low')}\n"
                        f"Issue: {issue}\n"
                        f"Recommendation: {recommendation}"
                    )
                else:
                    answer = str(ai_payload)
            except Exception:
                answer = f"Image uploaded successfully. AI response: {ai_payload}"
        else:
            answer = generate_text(
                f"Summarize the uploaded file '{file.filename}' and explain the key engineering observations or next steps.",
                system_prompt="You are a practical construction QA/QC assistant. Summarize uploaded documents, extract likely issues, and propose next actions.",
            )
    except Exception as exc:
        answer = f"File uploaded successfully, but automated analysis could not be completed: {exc}"

    ai_msg = ChatMessage(chat_id=chat_id, role="assistant", content=answer)
    db.add(ai_msg)
    db.commit()

    return JSONResponse(
        content={
            "filename": file.filename,
            "filepath": filepath,
            "message": answer,
        }
    )


# ============================================================
# Document Type Prompts
# ============================================================
@router.get("/api/document-types")
async def get_document_types():
    return JSONResponse(
        content={key: {"name": value["name"], "template": value["template"]} for key, value in DOCUMENT_PROMPTS.items()}
    )


@router.get("/api/disciplines")
async def get_disciplines():
    return JSONResponse(content={key: value for key, value in DISCIPLINE_PROMPTS.items()})


# Legacy endpoint for backward compatibility
@router.post("/assistant/chat")
async def assistant_chat_legacy(request: Request, db: Session = Depends(get_db)):
    user_data = request.session.get("user")
    user = None
    if user_data:
        user = db.query(User).filter(User.id == user_data["id"]).first()

    form = await request.form()
    prompt = (form.get("prompt") or "").strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        answer = generate_text(
            prompt,
            system_prompt=(
                "You are a practical engineering QA/QC assistant. "
                "Draft concise, structured guidance for construction and inspection work."
            ),
        )
    except AIUnavailable:
        answer = "AI service is temporarily unavailable. You can retry or continue working while we reconnect."

    if user:
        ai_request = AIRequest(
            user_id=user.id,
            company_id=user.company_id,
            workspace_id=user.workspace_id,
            request_type="assistant_chat",
            prompt=prompt,
            response=answer,
        )
        db.add(ai_request)
        db.commit()

    return JSONResponse(
        content={
            "answer": answer,
            "document_type": "Inspection Report",
            "template": "QA/QC Executive Summary",
            "prompt": prompt,
        }
    )
