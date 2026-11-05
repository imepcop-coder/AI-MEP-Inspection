import os
import secrets
from pathlib import Path
from urllib.parse import urlparse, quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth.tenant import apply_tenant_filter, get_authenticated_user, get_session_user, SESSION_SECRET
from app.database.db import Base, engine, get_db, ensure_sqlite_columns
from app.models.ai_request import AIRequest
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.inspection import Inspection
from app.models.notification import Notification
from app.models.ncr import NCR
from app.models.observation import Observation
from app.models.project import Project
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.models.workspace import Workspace
from app.models.uae_compliance import (
    UAEComplianceRecord,
    ContractorLicense,
    MaterialCertification,
    SafetyRecord,
)
from app.routes.admin import router as admin_router
from app.routes.assistant import router as assistant_router
from app.routes.auth import router as auth_router  # merged auth router (canonical)
from app.routes.calculators import router as calculator_router
from app.routes.mep_calculators import router as mep_calculator_router
from app.routes.plumbing import router as plumbing_router
from app.routes.plumbing_page import router as plumbing_page_router
from app.routes.plumbing_export import router as plumbing_export_router
from app.routes.inspection import router as inspection_router
from app.routes.notifications import router as notifications_router
from app.routes.project import router as project_router
from app.routes.report import router as reports_router
from app.routes.settings import router as settings_router
from app.routes.upload import router as upload_router
from app.services.workspace_service import WorkspaceService

BASE_DIR = Path(__file__).resolve().parent

import logging
import traceback
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError

# configure logger for application errors
logger = logging.getLogger("ai_mep")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


app = FastAPI(
    title="AI MEP Inspection Assistant",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)
ensure_sqlite_columns()

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="session",
    max_age=1209600,  # 14 days
    path='/',
    https_only=os.getenv("APP_ENV", "development").lower() == "production",
    same_site="lax",
)

# Temporary request/response session debug middleware (logs to session_debug.log)
@app.middleware("http")
async def session_debug_middleware(request: Request, call_next):
    import json, time
    log_path = Path(__file__).resolve().parents[1] / "session_debug.log"
    try:
        cookie_header = request.headers.get('cookie')
    except Exception:
        cookie_header = None
    try:
        cookies = dict(request.cookies)
    except Exception:
        cookies = None
    try:
        scope_session = request.scope.get('session') if hasattr(request, 'scope') else None
    except Exception:
        scope_session = None
    try:
        # accessing request.session may raise if SessionMiddleware not yet run, but it should be available
        session_prop = dict(request.session) if request.session is not None else None
    except Exception as e:
        session_prop = f"<error: {e}>"
    # initial current_user if present
    cur_user = getattr(request.state, 'current_user', None)

    entry = {
        'ts': time.time(),
        'path': str(request.url.path),
        'query': str(request.url.query),
        'cookie_header': cookie_header,
        'cookies': cookies,
        'scope_session': bool(scope_session) if scope_session is not None else None,
        'session_prop': session_prop,
        'state_current_user_before': repr(cur_user),
    }
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    response = await call_next(request)

    # log response set-cookie
    set_cookie = response.headers.get('set-cookie') if hasattr(response, 'headers') else None
    try:
        entry2 = {'ts': time.time(), 'path': str(request.url.path), 'set_cookie': set_cookie}
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry2) + "\n")
    except Exception:
        pass
    return response


def _is_safe_origin(origin: str | None, referer: str | None, host: str | None) -> bool:
    if not host:
        return False

    expected_host = host.split(":", 1)[0].lower()
    for header_value in (origin, referer):
        if not header_value:
            continue
        try:
            parsed = urlparse(header_value)
        except ValueError:
            continue
        if parsed.hostname and parsed.hostname.lower() == expected_host:
            return True
    return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Combined middleware: populate authentication context and enforce auth for protected routes.
    """
    import logging
    logger = logging.getLogger("ai_mep.auth")
    path = request.url.path or "/"
    db = next(get_db())
    try:
        # populate current_user from session provided by SessionMiddleware when available
        session_payload = None
        try:
            session_payload = request.scope.get("session") if hasattr(request, "scope") else None
        except Exception:
            session_payload = None
        if not session_payload:
            try:
                session_payload = request.session
            except Exception:
                session_payload = None

        logger.info("auth_middleware: session_payload keys=%s", list(session_payload.keys()) if isinstance(session_payload, dict) else None)

        if isinstance(session_payload, dict) and session_payload.get("user"):
            request.state.current_user = session_payload.get("user")
            request.state.user = request.state.current_user
        else:
            # fallback to DB lookup which may attempt to decode cookie
            try:
                current_user = get_session_user(request, db)
            except Exception as e:
                logger.info("auth_middleware: get_session_user error: %s", e)
                current_user = None
            request.state.current_user = current_user
            request.state.user = current_user

        logger.info("auth_middleware: current_user=%s", getattr(request.state, 'current_user', None))

        # enforcement: allow public resources
        if path.startswith("/static") or path.startswith("/uploads"):
            return await call_next(request)

        public_exact = {
            "/login",
            "/register",
            "/forgot-password",
            "/reset-password",
            "/favicon.ico",
            "/robots.txt",
            "/assistant/chat",
        }
        if path in public_exact:
            if getattr(request.state, "current_user", None) and path in ("/login", "/register"):
                return RedirectResponse(url="/dashboard", status_code=302)
            return await call_next(request)

        if path == "/calculators" or path.startswith("/calculators/"):
            return await call_next(request)

        if path.endswith("/health") or "/health" in path:
            return await call_next(request)

        if getattr(request.state, "current_user", None):
            return await call_next(request)

        # not authenticated -> preserve next and respond
        original = str(request.url.path)
        if request.url.query:
            original += "?" + request.url.query
        try:
            request.session["next"] = original
        except Exception:
            pass

        accept = request.headers.get("accept", "")
        is_api = request.url.path.startswith("/api/") or "application/json" in accept
        if is_api:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        try:
            next_q = quote(original, safe="")
        except Exception:
            next_q = original
        login_url = "/login"
        if next_q:
            login_url = f"/login?next={next_q}"
        return RedirectResponse(url=login_url, status_code=302)
    finally:
        db.close()


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path or "/"
    # Exempt public/auth endpoints from CSRF protection
    csrf_exempt = {
        "/login",
        "/register",
        "/forgot-password",
        "/reset-password",
        "/favicon.ico",
        "/robots.txt",
    }
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        # Skip CSRF for exempt paths, static/uploads, api, and health endpoints
        if path in csrf_exempt or path.startswith("/static") or path.startswith("/uploads") or path.startswith("/api/") or "/health" in path:
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            if not _is_safe_origin(
                request.headers.get("origin"),
                request.headers.get("referer"),
                request.headers.get("host"),
            ):
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed."})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Ensure SessionMiddleware runs before custom HTTP middleware so request.session is available
# to auth, debug, and security middleware handlers.
for i, mw in enumerate(app.user_middleware):
    if getattr(mw, 'cls', None) is SessionMiddleware:
        app.user_middleware.insert(0, app.user_middleware.pop(i))
        app.build_middleware_stack()
        break

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(reports_router)
app.include_router(assistant_router)
app.include_router(project_router)
app.include_router(calculator_router)
app.include_router(mep_calculator_router)
app.include_router(plumbing_router)
app.include_router(plumbing_page_router)
app.include_router(plumbing_export_router)
app.include_router(inspection_router)
app.include_router(settings_router)
app.include_router(notifications_router)
app.include_router(admin_router)


# Centralized friendly error responses
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse


def _render_friendly(request: Request, message: str, status_code: int = 500, hint: str | None = None):
    """Return TemplateResponse for HTML requests or JSONResponse for API calls.
    Technical details are logged only; end users receive a friendly message."""
    accept = request.headers.get("accept", "")
    # log at info level the user-friendly message; details logged separately by handlers
    if "application/json" in accept or request.url.path.startswith("/api/"):
        return JSONResponse(status_code=status_code, content={"error": message})
    # prefer template render for HTML
    try:
        return templates.TemplateResponse(
            request=request,
            name="errors/generic_error.html",
            context={"request": request, "message": message, "hint": hint},
            status_code=status_code,
        )
    except Exception:
        # fallback plain text (should not reveal details)
        return PlainTextResponse(content=message, status_code=status_code)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log technical details for developers/ops
    logger.info("Request validation failed: %s", str(exc))
    logger.debug("Traceback:\n%s", traceback.format_exc())

    # Attempt to build a structured field-errors mapping when possible
    from app.utils.validation import map_pydantic_errors
    field_errors = {}
    try:
        # Try to resolve a calculator page context from the request path to get friendly labels
        path_parts = request.url.path.strip('/').split('/')
        page = None
        # Patterns: /api/calculators/{category}/{slug} or /calculators/{category}/{slug} or /calculators/{slug}
        if len(path_parts) >= 4 and path_parts[0] == 'api' and path_parts[1] == 'calculators':
            category = path_parts[2]
            slug = path_parts[3]
            try:
                from app.routes.mep_calculators import get_calculator as _get_calc
                page = _get_calc(category, slug)
            except Exception:
                try:
                    from app.routes.calculators import get_calculator as _get_calc2
                    page = _get_calc2(category, slug)
                except Exception:
                    page = None
        elif len(path_parts) >= 2 and path_parts[0] == 'calculators':
            # Could be /calculators/{category}/{slug} or /calculators/{slug}
            if len(path_parts) >= 3:
                category = path_parts[1]
                slug = path_parts[2]
                try:
                    from app.routes.mep_calculators import get_calculator as _get_calc
                    page = _get_calc(category, slug)
                except Exception:
                    try:
                        from app.routes.calculators import _get_hvac_page as _get_hvac
                        page = _get_hvac()  # fallback not ideal
                    except Exception:
                        page = None
            else:
                slug = path_parts[1]
                try:
                    from app.routes.calculators import HVAC_CALCULATORS
                    page = HVAC_CALCULATORS.get(slug)
                except Exception:
                    page = None

        field_errors = map_pydantic_errors(page, exc.errors())
    except Exception:
        # Fallback: map simple loc -> message without labels
        for err in exc.errors():
            loc = err.get('loc', [])
            name = loc[-1] if isinstance(loc, (list, tuple)) and loc else str(loc)
            field_errors[str(name)] = err.get('msg', 'Invalid value')

    # If caller expects JSON or this is an API path, return structured JSON
    accept = request.headers.get('accept', '')
    if 'application/json' in accept or request.url.path.startswith('/api/'):
        return JSONResponse(status_code=422, content={"success": False, "errors": field_errors})

    # Otherwise render the calculator template if applicable
    try:
        # Attempt to read form values to preserve user input
        form_vals = {}
        try:
            form = await request.form()
            form_vals = dict(form)
        except Exception:
            form_vals = {}
        # If we identified a page, render calculator template with field_errors
        if 'page' in locals() and page:
            return templates.TemplateResponse(
                request=request,
                name='calculators/calculator_page.html',
                context={
                    'request': request,
                    'page': page,
                    'values': form_vals,
                    'result': None,
                    'error': 'Please check the highlighted fields and try again.',
                    'field_errors': field_errors,
                },
                status_code=422,
            )
    except Exception:
        logger.debug('Failed to render calculator page for validation error.')

    # Fallback to generic friendly message
    message = 'Please check the highlighted fields and try again.'
    return _render_friendly(request, message, status_code=422, hint='Please complete all required fields and use valid values.')


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    logger.info("Pydantic validation failed: %s", str(exc))
    logger.debug("Traceback:\n%s", traceback.format_exc())

    from app.utils.validation import map_pydantic_errors
    try:
        # try to resolve page as above
        path_parts = request.url.path.strip('/').split('/')
        page = None
        if len(path_parts) >= 3 and path_parts[0] == 'calculators':
            slug = path_parts[-1]
            try:
                from app.routes.mep_calculators import CALCULATOR_PAGES as CP
                page = CP.get(slug)
            except Exception:
                page = None
        field_errors = map_pydantic_errors(page, exc.errors())
    except Exception:
        field_errors = { (e.get('loc')[-1] if e.get('loc') else 'field'): e.get('msg') for e in exc.errors() }

    accept = request.headers.get('accept', '')
    if 'application/json' in accept or request.url.path.startswith('/api/'):
        return JSONResponse(status_code=422, content={"success": False, "errors": field_errors})

    # Try to render calculator template
    try:
        form_vals = {}
        try:
            form = await request.form()
            form_vals = dict(form)
        except Exception:
            form_vals = {}
        if page:
            return templates.TemplateResponse(
                request=request,
                name='calculators/calculator_page.html',
                context={
                    'request': request,
                    'page': page,
                    'values': form_vals,
                    'result': None,
                    'error': 'Please check the highlighted fields and try again.',
                    'field_errors': field_errors,
                },
                status_code=422,
            )
    except Exception:
        logger.debug('Failed to render calculator page for pydantic validation error.')

    message = 'Please check the highlighted fields and try again.'
    return _render_friendly(request, message, status_code=422, hint='Please complete all required fields and use valid values.')

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log detail but don't show technical text
    logger.warning("HTTP exception %s %s", exc.status_code, getattr(exc, "detail", None))

    # If the exception detail contains structured field errors, surface them to the client
    detail = getattr(exc, 'detail', None)
    if isinstance(detail, dict) and detail.get('errors'):
        # For API/JSON callers return structured JSON
        accept = request.headers.get('accept', '')
        if 'application/json' in accept or request.url.path.startswith('/api/'):
            return JSONResponse(status_code=exc.status_code, content={"success": False, "errors": detail.get('errors')})
        # For calculator pages, try to render the calculator template with field_errors
        try:
            path_parts = request.url.path.strip('/').split('/')
            page = None
            if len(path_parts) >= 3 and path_parts[0] == 'calculators':
                # /calculators/{category}/{slug} or /calculators/{slug}
                if len(path_parts) >= 4:
                    category = path_parts[1]
                    slug = path_parts[2]
                    from app.routes.mep_calculators import get_calculator as _get_calc
                    page = _get_calc(category, slug)
                else:
                    slug = path_parts[1]
                    from app.routes.calculators import HVAC_CALCULATORS
                    page = HVAC_CALCULATORS.get(slug)
            # preserve form values if present
            form_vals = {}
            try:
                form = await request.form()
                form_vals = dict(form)
            except Exception:
                form_vals = {}
            if page:
                return templates.TemplateResponse(
                    request=request,
                    name='calculators/calculator_page.html',
                    context={
                        'request': request,
                        'page': page,
                        'values': form_vals,
                        'result': None,
                        'error': 'Please check the highlighted fields and try again.',
                        'field_errors': detail.get('errors'),
                    },
                    status_code=exc.status_code,
                )
        except Exception:
            logger.debug('Failed to render calculator page for HTTPException with field errors.')

        # fallback to JSON with errors
        return JSONResponse(status_code=exc.status_code, content={"success": False, "errors": detail.get('errors')})

    # map common HTTP codes to friendly messages
    if exc.status_code == 404:
        return _render_friendly(request, "The requested page could not be found.", status_code=404)
    if exc.status_code in (401, 403):
        return _render_friendly(request, "You don't have permission to access this page.", status_code=exc.status_code)
    # default
    return _render_friendly(request, "An unexpected error occurred. Please try again later.", status_code=exc.status_code)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error: %s", str(exc))
    return _render_friendly(request, "We couldn't save or retrieve the requested data right now. Please try again.", status_code=500)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Capture technical details in the logs only
    logger.exception("Unhandled exception: %s", str(exc))
    # Do not expose any exception details to the client
    return _render_friendly(request, "Something went wrong while processing your request. Please try again.", status_code=500)



@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_data = request.session.get("user")
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    workspace = WorkspaceService(db)
    workspace.create_default_workspace(user)
    context = workspace.get_dashboard_context(user)
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)


@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request, db: Session = Depends(get_db)):
    user_data = request.session.get("user")
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_data["id"]).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    current_user = get_authenticated_user(request, db)
    project_count = apply_tenant_filter(db.query(Project), current_user).count()
    inspection_count = apply_tenant_filter(db.query(Inspection), current_user).count()
    approved_count = apply_tenant_filter(db.query(Inspection), current_user).filter(Inspection.status == "Approved").count()
    pending_count = apply_tenant_filter(db.query(Inspection), current_user).filter(Inspection.status == "Pending").count()
    open_ncrs = apply_tenant_filter(db.query(NCR), current_user).filter(NCR.status == "Open").count()
    closed_ncrs = apply_tenant_filter(db.query(NCR), current_user).filter(NCR.status != "Open").count()
    ai_reports = apply_tenant_filter(db.query(AIRequest), current_user).count()
    document_count = apply_tenant_filter(db.query(Document), current_user).count()

    pass_rate = round((approved_count / inspection_count * 100), 1) if inspection_count else 0.0
    failure_rate = round(100 - pass_rate, 1) if inspection_count else 0.0

    recent_inspections = (
        apply_tenant_filter(db.query(Inspection), current_user)
        .order_by(Inspection.created_at.desc())
        .limit(5)
        .all()
    )

    insights = []
    if recent_inspections:
        latest = recent_inspections[0]
        insights.append(f"Latest inspection {latest.inspection_no} is currently {latest.status}.")
    if open_ncrs:
        insights.append(f"There are {open_ncrs} unresolved NCRs in your workspace.")
    if project_count:
        insights.append(f"You have {project_count} active projects under review.")

    analytics_data = {
        "inspection_trend": [max(5, min(20, inspection_count + i)) for i in range(6)],
        "pass_fail": [int(pass_rate), int(failure_rate)],
        "ncr_trend": [max(1, open_ncrs + i) for i in range(5)],
        "ai_usage": [max(1, ai_reports + i) for i in range(5)],
        "timeline": [min(100, 40 + (i * 15)) for i in range(4)],
    }

    context = {
        "user": user,
        "kpis": {
            "active_projects": project_count,
            "total_inspections": inspection_count,
            "open_ncrs": open_ncrs,
            "closed_ncrs": closed_ncrs,
            "inspection_pass_rate": pass_rate,
            "inspection_failure_rate": failure_rate,
            "ai_reports_generated": ai_reports,
            "team_productivity": round(min(100.0, 70 + (pass_rate * 0.2)), 1),
            "avg_inspection_time": "18m",
            "documents_generated": document_count,
            "pending_actions": pending_count,
            "monthly_revenue": "$0",
        },
        "insights": insights or ["No inspection activity recorded yet. Start a new inspection to populate analytics."],
        "leaders": [
            {"name": user.full_name, "metric": f"{inspection_count} inspections", "delta": "+0%"},
            {"name": "Workspace", "metric": f"{project_count} projects", "delta": "+0%"},
        ],
        "analytics_data": analytics_data,
    }
    return templates.TemplateResponse(request=request, name="analytics.html", context=context)

