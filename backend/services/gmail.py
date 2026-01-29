import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth import google_auth


class GmailService:
    """Service for interacting with Gmail API."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        """Get or create Gmail API service."""
        credentials = google_auth.get_credentials()
        if not credentials:
            raise ValueError("Not authenticated. Please login first.")

        if not self._service:
            self._service = build("gmail", "v1", credentials=credentials)
        return self._service

    def list_emails(
        self,
        max_results: int = 10,
        query: str = "",
        label_ids: list = None,
    ) -> list:
        """
        List emails from inbox.

        Args:
            max_results: Maximum number of emails to return
            query: Gmail search query (e.g., "is:unread", "from:someone@example.com")
            label_ids: List of label IDs to filter by (e.g., ["INBOX", "UNREAD"])

        Returns:
            List of email summaries with id, subject, from, date, snippet
        """
        try:
            service = self._get_service()

            # Build the request
            request_params = {
                "userId": "me",
                "maxResults": max_results,
            }
            if query:
                request_params["q"] = query
            if label_ids:
                request_params["labelIds"] = label_ids

            results = service.users().messages().list(**request_params).execute()
            messages = results.get("messages", [])

            emails = []
            for msg in messages:
                email_data = self.get_email(msg["id"])
                if email_data:
                    emails.append(email_data)

            return emails

        except HttpError as error:
            print(f"Gmail API error: {error}")
            return []

    def get_email(self, email_id: str) -> Optional[dict]:
        """
        Get a specific email by ID.

        Args:
            email_id: The email message ID

        Returns:
            Email details including subject, from, to, date, body, snippet
        """
        try:
            service = self._get_service()
            message = service.users().messages().get(
                userId="me",
                id=email_id,
                format="full"
            ).execute()

            # Extract headers
            headers = message.get("payload", {}).get("headers", [])
            header_dict = {h["name"].lower(): h["value"] for h in headers}

            # Extract body
            body = self._extract_body(message.get("payload", {}))

            return {
                "id": message["id"],
                "thread_id": message["threadId"],
                "subject": header_dict.get("subject", "(No Subject)"),
                "from": header_dict.get("from", "Unknown"),
                "to": header_dict.get("to", ""),
                "date": header_dict.get("date", ""),
                "snippet": message.get("snippet", ""),
                "body": body,
                "labels": message.get("labelIds", []),
            }

        except HttpError as error:
            print(f"Gmail API error: {error}")
            return None

    def _extract_body(self, payload: dict) -> str:
        """Extract email body from payload."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and part["body"].get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
                elif part["mimeType"] == "text/html" and part["body"].get("data") and not body:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                elif "parts" in part:
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> Optional[dict]:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, body is treated as HTML

        Returns:
            Sent message details or None on failure
        """
        try:
            service = self._get_service()

            if html:
                message = MIMEMultipart("alternative")
                message.attach(MIMEText(body, "html"))
            else:
                message = MIMEText(body)

            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            sent_message = service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            return {
                "id": sent_message["id"],
                "thread_id": sent_message["threadId"],
                "message": f"Email sent successfully to {to}",
            }

        except HttpError as error:
            print(f"Gmail API error: {error}")
            return None

    def search_emails(self, query: str, max_results: int = 10) -> list:
        """
        Search emails using Gmail query syntax.

        Args:
            query: Gmail search query (e.g., "from:someone subject:meeting")
            max_results: Maximum results to return

        Returns:
            List of matching emails
        """
        return self.list_emails(max_results=max_results, query=query)

    def get_unread_emails(self, max_results: int = 10) -> list:
        """Get unread emails."""
        return self.list_emails(max_results=max_results, query="is:unread")

    def mark_as_read(self, email_id: str) -> bool:
        """Mark an email as read."""
        try:
            service = self._get_service()
            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return False

    def mark_as_unread(self, email_id: str) -> bool:
        """Mark an email as unread."""
        try:
            service = self._get_service()
            service.users().messages().modify(
                userId="me",
                id=email_id,
                body={"addLabelIds": ["UNREAD"]}
            ).execute()
            return True
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return False

    def delete_email(self, email_id: str) -> bool:
        """
        Move an email to trash.

        Args:
            email_id: The email message ID

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service()
            service.users().messages().trash(userId="me", id=email_id).execute()
            return True
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return False

    def permanently_delete_email(self, email_id: str) -> bool:
        """
        Permanently delete an email (cannot be recovered).

        Args:
            email_id: The email message ID

        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._get_service()
            service.users().messages().delete(userId="me", id=email_id).execute()
            return True
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return False

    def get_labels(self) -> list:
        """Get all Gmail labels."""
        try:
            service = self._get_service()
            results = service.users().labels().list(userId="me").execute()
            return results.get("labels", [])
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return []


# Singleton instance
gmail_service = GmailService()
