from datetime import datetime, timedelta
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth import google_auth


class CalendarService:
    """Service for interacting with Google Calendar API."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        """Get or create Calendar API service."""
        credentials = google_auth.get_credentials()
        if not credentials:
            raise ValueError("Not authenticated. Please login first.")

        if not self._service:
            self._service = build("calendar", "v3", credentials=credentials)
        return self._service

    def list_events(
        self,
        max_results: int = 10,
        time_min: datetime = None,
        time_max: datetime = None,
        calendar_id: str = "primary",
    ) -> list:
        """
        List upcoming events from calendar.

        Args:
            max_results: Maximum number of events to return
            time_min: Start time filter (defaults to now)
            time_max: End time filter (optional)
            calendar_id: Calendar ID (defaults to primary)

        Returns:
            List of event summaries
        """
        try:
            service = self._get_service()

            if not time_min:
                time_min = datetime.utcnow()

            request_params = {
                "calendarId": calendar_id,
                "timeMin": time_min.isoformat() + "Z",
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }

            if time_max:
                request_params["timeMax"] = time_max.isoformat() + "Z"

            events_result = service.events().list(**request_params).execute()
            events = events_result.get("items", [])

            return [self._format_event(event) for event in events]

        except HttpError as error:
            print(f"Calendar API error: {error}")
            return []

    def _format_event(self, event: dict) -> dict:
        """Format a calendar event for display."""
        start = event.get("start", {})
        end = event.get("end", {})

        return {
            "id": event.get("id"),
            "summary": event.get("summary", "(No title)"),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "all_day": "date" in start and "dateTime" not in start,
            "attendees": [
                {
                    "email": a.get("email"),
                    "name": a.get("displayName", ""),
                    "response": a.get("responseStatus", ""),
                }
                for a in event.get("attendees", [])
            ],
            "organizer": event.get("organizer", {}).get("email", ""),
            "status": event.get("status", ""),
            "html_link": event.get("htmlLink", ""),
        }

    def get_event(self, event_id: str, calendar_id: str = "primary") -> Optional[dict]:
        """
        Get a specific event by ID.

        Args:
            event_id: The event ID
            calendar_id: Calendar ID (defaults to primary)

        Returns:
            Event details or None
        """
        try:
            service = self._get_service()
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            return self._format_event(event)
        except HttpError as error:
            print(f"Calendar API error: {error}")
            return None

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime = None,
        description: str = "",
        location: str = "",
        attendees: list = None,
        all_day: bool = False,
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> Optional[dict]:
        """
        Create a new calendar event.

        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time (defaults to 1 hour after start)
            description: Event description
            location: Event location
            attendees: List of attendee email addresses
            all_day: If True, create an all-day event
            calendar_id: Calendar ID (defaults to primary)
            send_notifications: Whether to send notifications to attendees

        Returns:
            Created event details or None
        """
        try:
            service = self._get_service()

            if not end_time:
                end_time = start_time + timedelta(hours=1)

            event_body = {
                "summary": summary,
                "description": description,
                "location": location,
            }

            if all_day:
                event_body["start"] = {"date": start_time.strftime("%Y-%m-%d")}
                event_body["end"] = {"date": end_time.strftime("%Y-%m-%d")}
            else:
                event_body["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                }
                event_body["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                }

            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]

            event = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
                sendNotifications=send_notifications,
            ).execute()

            return self._format_event(event)

        except HttpError as error:
            print(f"Calendar API error: {error}")
            return None

    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        description: str = None,
        location: str = None,
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> Optional[dict]:
        """
        Update an existing calendar event.

        Args:
            event_id: The event ID to update
            summary: New event title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            calendar_id: Calendar ID (defaults to primary)
            send_notifications: Whether to send notifications

        Returns:
            Updated event details or None
        """
        try:
            service = self._get_service()

            # Get existing event
            event = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Update fields if provided
            if summary is not None:
                event["summary"] = summary
            if description is not None:
                event["description"] = description
            if location is not None:
                event["location"] = location
            if start_time is not None:
                event["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                }
            if end_time is not None:
                event["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                }

            updated_event = service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendNotifications=send_notifications,
            ).execute()

            return self._format_event(updated_event)

        except HttpError as error:
            print(f"Calendar API error: {error}")
            return None

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        send_notifications: bool = True,
    ) -> bool:
        """
        Delete a calendar event.

        Args:
            event_id: The event ID to delete
            calendar_id: Calendar ID (defaults to primary)
            send_notifications: Whether to send cancellation notifications

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service()
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendNotifications=send_notifications,
            ).execute()
            return True
        except HttpError as error:
            print(f"Calendar API error: {error}")
            return False

    def get_today_events(self) -> list:
        """Get all events for today."""
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        return self.list_events(time_min=start_of_day, time_max=end_of_day, max_results=50)

    def get_week_events(self) -> list:
        """Get all events for the current week."""
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)
        return self.list_events(time_min=start_of_week, time_max=end_of_week, max_results=100)

    def get_calendars(self) -> list:
        """Get list of all calendars."""
        try:
            service = self._get_service()
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])

            return [
                {
                    "id": cal.get("id"),
                    "summary": cal.get("summary"),
                    "description": cal.get("description", ""),
                    "primary": cal.get("primary", False),
                    "access_role": cal.get("accessRole", ""),
                }
                for cal in calendars
            ]
        except HttpError as error:
            print(f"Calendar API error: {error}")
            return []

    def find_free_slots(
        self,
        duration_minutes: int = 60,
        days_ahead: int = 7,
        start_hour: int = 9,
        end_hour: int = 17,
    ) -> list:
        """
        Find free time slots in the calendar.

        Args:
            duration_minutes: Required duration for the slot
            days_ahead: Number of days to look ahead
            start_hour: Working hours start (0-23)
            end_hour: Working hours end (0-23)

        Returns:
            List of free time slots
        """
        try:
            now = datetime.utcnow()
            end_date = now + timedelta(days=days_ahead)

            events = self.list_events(
                time_min=now,
                time_max=end_date,
                max_results=250,
            )

            # Build list of busy times
            busy_times = []
            for event in events:
                if event["start"] and event["end"]:
                    try:
                        start = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(event["end"].replace("Z", "+00:00"))
                        busy_times.append((start, end))
                    except (ValueError, TypeError):
                        continue

            # Find free slots
            free_slots = []
            current_date = now.date()

            for day_offset in range(days_ahead):
                check_date = current_date + timedelta(days=day_offset)
                day_start = datetime(
                    check_date.year, check_date.month, check_date.day,
                    start_hour, 0, 0
                )
                day_end = datetime(
                    check_date.year, check_date.month, check_date.day,
                    end_hour, 0, 0
                )

                # Skip if day_start is in the past
                if day_start < now:
                    day_start = now

                # Check each potential slot
                slot_start = day_start
                while slot_start + timedelta(minutes=duration_minutes) <= day_end:
                    slot_end = slot_start + timedelta(minutes=duration_minutes)

                    # Check if slot overlaps with any busy time
                    is_free = True
                    for busy_start, busy_end in busy_times:
                        if not (slot_end <= busy_start or slot_start >= busy_end):
                            is_free = False
                            break

                    if is_free:
                        free_slots.append({
                            "start": slot_start.isoformat(),
                            "end": slot_end.isoformat(),
                            "date": check_date.strftime("%Y-%m-%d"),
                        })

                    slot_start += timedelta(minutes=30)  # Check every 30 minutes

                if len(free_slots) >= 20:  # Limit results
                    break

            return free_slots[:20]

        except Exception as error:
            print(f"Error finding free slots: {error}")
            return []


# Singleton instance
calendar_service = CalendarService()
