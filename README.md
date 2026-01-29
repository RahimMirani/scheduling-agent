# Scheduling Agent

AI-powered scheduling assistant with Gmail and Google Calendar integration, powered by Google Gemini.

## Features

- Natural language conversation interface
- Gmail integration (read, send, search, delete emails)
- Google Calendar integration (view, create, update, delete events)
- Gemini AI for intelligent query understanding

## Setup

### Prerequisites

- Python 3.10+
- Google Cloud Project with enabled APIs:
  - Gmail API
  - Google Calendar API
  - Generative Language API (Gemini)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/RahimMirani/scheduling-agent.git
   cd scheduling-agent
   ```

2. Create virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up credentials:
   - Download OAuth 2.0 credentials from Google Cloud Console
   - Save as `backend/credentials.json`
   - Copy `.env.example` to `.env` and fill in your values:
     ```bash
     cp .env.example .env
     ```

4. Run the application:
   ```bash
   python main.py
   ```

5. Open http://localhost:8000 in your browser

## Project Structure

```
scheduling-agent/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── auth.py              # Google OAuth handling
│   ├── services/
│   │   ├── gmail.py         # Gmail operations
│   │   ├── calendar.py      # Calendar operations
│   │   └── agent.py         # Gemini agent
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── README.md
```

## Usage

1. Authenticate with your Google account
2. Chat with the agent using natural language:
   - "Do I have any important emails today?"
   - "What's on my calendar this week?"
   - "Schedule a meeting with John tomorrow at 2pm"
   - "Send an email to alice@example.com about the project update"
