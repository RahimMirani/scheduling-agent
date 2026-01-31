from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import uvicorn
import os

from config import settings
from auth import google_auth
from services.gmail import gmail_service
from services.calendar import calendar_service
from services.agent import scheduling_agent

app = FastAPI(
    title="Scheduling Agent",
    description="AI-powered scheduling assistant with Gmail and Calendar integration",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------Frontend Routes Mounting Via Backend-----------------------

# Mount static files for frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Explicit routes for CSS and JS to ensure proper content types
@app.get("/static/styles.css")
async def serve_css():
    """Serve CSS file with proper headers."""
    css_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.css")
    if os.path.exists(css_path):
        return FileResponse(
            css_path,
            media_type="text/css",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/static/app.js")
async def serve_js():
    """Serve JS file with proper headers."""
    js_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "app.js")
    if os.path.exists(js_path):
        return FileResponse(
            js_path,
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="JS file not found")

# Also serve at root level for relative path support (when opening index.html directly)
@app.get("/styles.css")
async def serve_css_root():
    """Serve CSS file at root level."""
    return await serve_css()

@app.get("/app.js")
async def serve_js_root():
    """Serve JS file at root level."""
    return await serve_js()

# Add no-cache headers for static files in development
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/")
async def root():
    """Serve the frontend."""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Scheduling Agent API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============== Authentication Routes ==============

@app.get("/auth/status")
async def auth_status():
    """Check if user is authenticated."""
    is_authenticated = google_auth.is_authenticated()
    return {"authenticated": is_authenticated}


@app.get("/auth/login")
async def auth_login(request: Request):
    """Initiate Google OAuth login flow."""
    redirect_uri = str(request.url_for("auth_callback"))

    try:
        authorization_url = google_auth.get_authorization_url(redirect_uri)
        return {"authorization_url": authorization_url}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback from Google."""
    authorization_response = str(request.url)

    success = google_auth.handle_callback(authorization_response)

    if success:
        # Redirect to frontend after successful auth
        return RedirectResponse(url="/")
    else:
        raise HTTPException(status_code=400, detail="Authentication failed")


@app.get("/auth/logout")
async def auth_logout():
    """Logout and clear credentials."""
    google_auth.logout()
    return {"message": "Logged out successfully"}


# ============== Gmail Routes ==============

def require_auth():
    """Check authentication before Gmail operations."""
    if not google_auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated. Please login first.")


@app.get("/api/gmail/emails")
async def get_emails(max_results: int = 10, query: str = ""):
    """Get emails from inbox."""
    require_auth()
    emails = gmail_service.list_emails(max_results=max_results, query=query)
    return {"emails": emails, "count": len(emails)}


@app.get("/api/gmail/emails/unread")
async def get_unread_emails(max_results: int = 10):
    """Get unread emails."""
    require_auth()
    emails = gmail_service.get_unread_emails(max_results=max_results)
    return {"emails": emails, "count": len(emails)}


@app.get("/api/gmail/emails/{email_id}")
async def get_email(email_id: str):
    """Get a specific email by ID."""
    require_auth()
    email = gmail_service.get_email(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@app.post("/api/gmail/send")
async def send_email(request: Request):
    """Send an email."""
    require_auth()
    data = await request.json()

    to = data.get("to")
    subject = data.get("subject")
    body = data.get("body")
    html = data.get("html", False)

    if not all([to, subject, body]):
        raise HTTPException(status_code=400, detail="Missing required fields: to, subject, body")

    result = gmail_service.send_email(to=to, subject=subject, body=body, html=html)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to send email")
    return result


@app.post("/api/gmail/emails/{email_id}/read")
async def mark_email_read(email_id: str):
    """Mark an email as read."""
    require_auth()
    success = gmail_service.mark_as_read(email_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to mark email as read")
    return {"message": "Email marked as read"}


@app.post("/api/gmail/emails/{email_id}/unread")
async def mark_email_unread(email_id: str):
    """Mark an email as unread."""
    require_auth()
    success = gmail_service.mark_as_unread(email_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to mark email as unread")
    return {"message": "Email marked as unread"}


@app.delete("/api/gmail/emails/{email_id}")
async def delete_email(email_id: str, permanent: bool = False):
    """Delete an email (move to trash or permanently delete)."""
    require_auth()
    if permanent:
        success = gmail_service.permanently_delete_email(email_id)
    else:
        success = gmail_service.delete_email(email_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete email")
    return {"message": "Email deleted successfully"}


@app.get("/api/gmail/labels")
async def get_labels():
    """Get all Gmail labels."""
    require_auth()
    labels = gmail_service.get_labels()
    return {"labels": labels}


# ============== Calendar Routes ==============

@app.get("/api/calendar/events")
async def get_events(max_results: int = 10):
    """Get upcoming calendar events."""
    require_auth()
    events = calendar_service.list_events(max_results=max_results)
    return {"events": events, "count": len(events)}


@app.get("/api/calendar/events/today")
async def get_today_events():
    """Get today's calendar events."""
    require_auth()
    events = calendar_service.get_today_events()
    return {"events": events, "count": len(events)}


@app.get("/api/calendar/events/week")
async def get_week_events():
    """Get this week's calendar events."""
    require_auth()
    events = calendar_service.get_week_events()
    return {"events": events, "count": len(events)}


@app.get("/api/calendar/events/{event_id}")
async def get_event(event_id: str):
    """Get a specific calendar event."""
    require_auth()
    event = calendar_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.post("/api/calendar/events")
async def create_event(request: Request):
    """Create a new calendar event."""
    require_auth()
    data = await request.json()

    from datetime import datetime

    summary = data.get("summary")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    description = data.get("description", "")
    location = data.get("location", "")
    attendees = data.get("attendees", [])
    all_day = data.get("all_day", False)

    if not summary or not start_time_str:
        raise HTTPException(status_code=400, detail="Missing required fields: summary, start_time")

    try:
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00")) if end_time_str else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")

    event = calendar_service.create_event(
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
        attendees=attendees,
        all_day=all_day,
    )

    if not event:
        raise HTTPException(status_code=500, detail="Failed to create event")
    return event


@app.put("/api/calendar/events/{event_id}")
async def update_event(event_id: str, request: Request):
    """Update an existing calendar event."""
    require_auth()
    data = await request.json()

    from datetime import datetime

    summary = data.get("summary")
    start_time_str = data.get("start_time")
    end_time_str = data.get("end_time")
    description = data.get("description")
    location = data.get("location")

    start_time = None
    end_time = None

    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    event = calendar_service.update_event(
        event_id=event_id,
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
    )

    if not event:
        raise HTTPException(status_code=500, detail="Failed to update event")
    return event


@app.delete("/api/calendar/events/{event_id}")
async def delete_event(event_id: str):
    """Delete a calendar event."""
    require_auth()
    success = calendar_service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete event")
    return {"message": "Event deleted successfully"}


@app.get("/api/calendar/calendars")
async def get_calendars():
    """Get list of all calendars."""
    require_auth()
    calendars = calendar_service.get_calendars()
    return {"calendars": calendars}


@app.get("/api/calendar/free-slots")
async def get_free_slots(
    duration_minutes: int = 60,
    days_ahead: int = 7,
    start_hour: int = 9,
    end_hour: int = 17,
):
    """Find free time slots in the calendar."""
    require_auth()
    slots = calendar_service.find_free_slots(
        duration_minutes=duration_minutes,
        days_ahead=days_ahead,
        start_hour=start_hour,
        end_hour=end_hour,
    )
    return {"free_slots": slots, "count": len(slots)}


# ============== Agent Chat Routes ==============

@app.post("/api/chat")
async def chat(request: Request):
    """Send a message to the scheduling agent."""
    require_auth()

    data = await request.json()
    message = data.get("message")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    response = scheduling_agent.send_message(message)
    return {"response": response}


@app.post("/api/chat/reset")
async def reset_chat():
    """Reset the chat session."""
    scheduling_agent.reset_chat()
    return {"message": "Chat session reset"}


if __name__ == "__main__":
    from urllib.parse import urlparse
    
    url = os.getenv("APP_URL", "http://localhost:8000")
    parsed = urlparse(url)
    
    uvicorn.run(
        "main:app",
        host=parsed.hostname or "localhost",
        port=parsed.port or 8000,
        reload=True,
    )
