from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import uvicorn
import os

from config import settings
from auth import google_auth
from services.gmail import gmail_service

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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
