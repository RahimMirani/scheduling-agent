import json
from datetime import datetime, timedelta
from typing import Optional
import google.generativeai as genai

from config import settings
from services.gmail import gmail_service
from services.calendar import calendar_service


class SchedulingAgent:
    """AI-powered scheduling agent using Gemini with function calling."""

    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            tools=self._get_tools(),
            system_instruction=self._get_system_prompt(),
        )
        self.chat = None

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        today = datetime.now().strftime("%A, %B %d, %Y")
        current_time = datetime.now().strftime("%I:%M %p")

        return f"""You are a helpful scheduling assistant with access to the user's Gmail and Google Calendar.

Today's date is {today} and the current time is {current_time}.

Your capabilities:
- Read, search, and manage emails (Gmail)
- View, create, update, and delete calendar events
- Find free time slots for scheduling
- Send emails on behalf of the user

Guidelines:
1. Be concise and helpful in your responses
2. When showing emails or events, summarize the key information
3. Ask for confirmation before sending emails or creating/modifying events
4. When scheduling meetings, suggest available time slots if not specified
5. Format dates and times in a user-friendly way
6. If a request is unclear, ask clarifying questions

Always use the available functions to fetch real data - never make up information about emails or calendar events."""

    def _get_tools(self) -> list:
        """Define the tools/functions available to the agent."""
        return [
            # Gmail functions
            {
                "function_declarations": [
                    {
                        "name": "get_emails",
                        "description": "Get a list of emails from the inbox. Use this to check for emails, find specific emails, or see recent messages.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of emails to return (default 10)",
                                },
                                "query": {
                                    "type": "string",
                                    "description": "Gmail search query (e.g., 'is:unread', 'from:someone@example.com', 'subject:meeting')",
                                },
                            },
                        },
                    },
                    {
                        "name": "get_unread_emails",
                        "description": "Get unread emails from the inbox.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of emails to return (default 10)",
                                },
                            },
                        },
                    },
                    {
                        "name": "get_email_details",
                        "description": "Get the full details of a specific email including the body content.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "email_id": {
                                    "type": "string",
                                    "description": "The ID of the email to retrieve",
                                },
                            },
                            "required": ["email_id"],
                        },
                    },
                    {
                        "name": "send_email",
                        "description": "Send an email to a recipient.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "to": {
                                    "type": "string",
                                    "description": "Recipient email address",
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "Email subject line",
                                },
                                "body": {
                                    "type": "string",
                                    "description": "Email body content",
                                },
                            },
                            "required": ["to", "subject", "body"],
                        },
                    },
                    {
                        "name": "search_emails",
                        "description": "Search emails using Gmail query syntax.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Gmail search query (e.g., 'from:john subject:project')",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of results (default 10)",
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "delete_email",
                        "description": "Move an email to trash.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "email_id": {
                                    "type": "string",
                                    "description": "The ID of the email to delete",
                                },
                            },
                            "required": ["email_id"],
                        },
                    },
                    {
                        "name": "mark_email_as_read",
                        "description": "Mark an email as read.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "email_id": {
                                    "type": "string",
                                    "description": "The ID of the email to mark as read",
                                },
                            },
                            "required": ["email_id"],
                        },
                    },
                    # Calendar functions
                    {
                        "name": "get_calendar_events",
                        "description": "Get upcoming calendar events.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "max_results": {
                                    "type": "integer",
                                    "description": "Maximum number of events to return (default 10)",
                                },
                            },
                        },
                    },
                    {
                        "name": "get_today_events",
                        "description": "Get all calendar events for today.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                    {
                        "name": "get_week_events",
                        "description": "Get all calendar events for the current week.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                    {
                        "name": "create_calendar_event",
                        "description": "Create a new calendar event.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "Event title/summary",
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "Event start time in ISO format (e.g., '2024-01-15T14:00:00')",
                                },
                                "end_time": {
                                    "type": "string",
                                    "description": "Event end time in ISO format (optional, defaults to 1 hour after start)",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Event description (optional)",
                                },
                                "location": {
                                    "type": "string",
                                    "description": "Event location (optional)",
                                },
                                "attendees": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of attendee email addresses (optional)",
                                },
                            },
                            "required": ["summary", "start_time"],
                        },
                    },
                    {
                        "name": "update_calendar_event",
                        "description": "Update an existing calendar event.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "event_id": {
                                    "type": "string",
                                    "description": "The ID of the event to update",
                                },
                                "summary": {
                                    "type": "string",
                                    "description": "New event title (optional)",
                                },
                                "start_time": {
                                    "type": "string",
                                    "description": "New start time in ISO format (optional)",
                                },
                                "end_time": {
                                    "type": "string",
                                    "description": "New end time in ISO format (optional)",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "New description (optional)",
                                },
                                "location": {
                                    "type": "string",
                                    "description": "New location (optional)",
                                },
                            },
                            "required": ["event_id"],
                        },
                    },
                    {
                        "name": "delete_calendar_event",
                        "description": "Delete a calendar event.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "event_id": {
                                    "type": "string",
                                    "description": "The ID of the event to delete",
                                },
                            },
                            "required": ["event_id"],
                        },
                    },
                    {
                        "name": "find_free_slots",
                        "description": "Find available free time slots in the calendar for scheduling.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "duration_minutes": {
                                    "type": "integer",
                                    "description": "Required duration for the meeting in minutes (default 60)",
                                },
                                "days_ahead": {
                                    "type": "integer",
                                    "description": "Number of days to look ahead (default 7)",
                                },
                            },
                        },
                    },
                ]
            }
        ]

    def _execute_function(self, function_name: str, args: dict) -> dict:
        """Execute a function call and return the result."""
        try:
            if function_name == "get_emails":
                max_results = args.get("max_results", 10)
                query = args.get("query", "")
                emails = gmail_service.list_emails(max_results=max_results, query=query)
                return {"success": True, "emails": emails, "count": len(emails)}

            elif function_name == "get_unread_emails":
                max_results = args.get("max_results", 10)
                emails = gmail_service.get_unread_emails(max_results=max_results)
                return {"success": True, "emails": emails, "count": len(emails)}

            elif function_name == "get_email_details":
                email_id = args.get("email_id")
                email = gmail_service.get_email(email_id)
                if email:
                    return {"success": True, "email": email}
                return {"success": False, "error": "Email not found"}

            elif function_name == "send_email":
                result = gmail_service.send_email(
                    to=args.get("to"),
                    subject=args.get("subject"),
                    body=args.get("body"),
                )
                if result:
                    return {"success": True, "message": f"Email sent successfully to {args.get('to')}"}
                return {"success": False, "error": "Failed to send email"}

            elif function_name == "search_emails":
                query = args.get("query")
                max_results = args.get("max_results", 10)
                emails = gmail_service.search_emails(query=query, max_results=max_results)
                return {"success": True, "emails": emails, "count": len(emails)}

            elif function_name == "delete_email":
                email_id = args.get("email_id")
                success = gmail_service.delete_email(email_id)
                if success:
                    return {"success": True, "message": "Email moved to trash"}
                return {"success": False, "error": "Failed to delete email"}

            elif function_name == "mark_email_as_read":
                email_id = args.get("email_id")
                success = gmail_service.mark_as_read(email_id)
                if success:
                    return {"success": True, "message": "Email marked as read"}
                return {"success": False, "error": "Failed to mark email as read"}

            elif function_name == "get_calendar_events":
                max_results = args.get("max_results", 10)
                events = calendar_service.list_events(max_results=max_results)
                return {"success": True, "events": events, "count": len(events)}

            elif function_name == "get_today_events":
                events = calendar_service.get_today_events()
                return {"success": True, "events": events, "count": len(events)}

            elif function_name == "get_week_events":
                events = calendar_service.get_week_events()
                return {"success": True, "events": events, "count": len(events)}

            elif function_name == "create_calendar_event":
                start_time = datetime.fromisoformat(args.get("start_time"))
                end_time = None
                if args.get("end_time"):
                    end_time = datetime.fromisoformat(args.get("end_time"))

                event = calendar_service.create_event(
                    summary=args.get("summary"),
                    start_time=start_time,
                    end_time=end_time,
                    description=args.get("description", ""),
                    location=args.get("location", ""),
                    attendees=args.get("attendees", []),
                )
                if event:
                    return {"success": True, "event": event, "message": "Event created successfully"}
                return {"success": False, "error": "Failed to create event"}

            elif function_name == "update_calendar_event":
                event_id = args.get("event_id")
                start_time = None
                end_time = None

                if args.get("start_time"):
                    start_time = datetime.fromisoformat(args.get("start_time"))
                if args.get("end_time"):
                    end_time = datetime.fromisoformat(args.get("end_time"))

                event = calendar_service.update_event(
                    event_id=event_id,
                    summary=args.get("summary"),
                    start_time=start_time,
                    end_time=end_time,
                    description=args.get("description"),
                    location=args.get("location"),
                )
                if event:
                    return {"success": True, "event": event, "message": "Event updated successfully"}
                return {"success": False, "error": "Failed to update event"}

            elif function_name == "delete_calendar_event":
                event_id = args.get("event_id")
                success = calendar_service.delete_event(event_id)
                if success:
                    return {"success": True, "message": "Event deleted successfully"}
                return {"success": False, "error": "Failed to delete event"}

            elif function_name == "find_free_slots":
                duration = args.get("duration_minutes", 60)
                days = args.get("days_ahead", 7)
                slots = calendar_service.find_free_slots(
                    duration_minutes=duration,
                    days_ahead=days,
                )
                return {"success": True, "free_slots": slots, "count": len(slots)}

            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_chat(self):
        """Start a new chat session."""
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)

    def send_message(self, message: str) -> str:
        """
        Send a message to the agent and get a response.

        Args:
            message: The user's message

        Returns:
            The agent's response
        """
        if not self.chat:
            self.start_chat()

        try:
            response = self.chat.send_message(message)

            # Handle function calls
            while response.candidates[0].content.parts:
                function_calls = [
                    part.function_call
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "function_call") and part.function_call.name
                ]

                if not function_calls:
                    # No function calls, return the text response
                    text_parts = [
                        part.text
                        for part in response.candidates[0].content.parts
                        if hasattr(part, "text") and part.text
                    ]
                    return "\n".join(text_parts) if text_parts else "I couldn't process that request."

                # Execute function calls and send results back
                function_responses = []
                for fc in function_calls:
                    args = dict(fc.args) if fc.args else {}
                    result = self._execute_function(fc.name, args)
                    function_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc.name,
                                response={"result": json.dumps(result)},
                            )
                        )
                    )

                # Send function results back to the model
                response = self.chat.send_message(function_responses)

            # Extract final text response
            text_parts = [
                part.text
                for part in response.candidates[0].content.parts
                if hasattr(part, "text") and part.text
            ]
            return "\n".join(text_parts) if text_parts else "Done!"

        except Exception as e:
            return f"Error: {str(e)}"

    def reset_chat(self):
        """Reset the chat session."""
        self.chat = None


# Singleton instance
scheduling_agent = SchedulingAgent()
