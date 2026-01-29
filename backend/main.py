from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import uvicorn
import os

from config import settings
from auth import google_auth

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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
