import os
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class Gmail:

    def __init__(self):
        self.creds = self.authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def authenticate(self):
        creds = None
        # Load existing credentials if available
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # If credentials are invalid, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return creds
    
    def search_emails(self, query):
        """Yield all emails matching query
        """

        page_token = None

        while True:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=100, pageToken=page_token).execute()
            for message in results.get('messages', []):
                yield message
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break  # No more pages
        
    def get_email(self, id):
        return self.service.users().messages().get(userId='me', id=id).execute()

    def extract_email_content(self, message):
        """
        Extract email subject and body from Gmail API message
        
        Args:
            message: The message object returned by service.users().messages().get()
        
        Returns:
            dict: Contains 'subject', 'sender', 'plain_body', and 'html_body' keys
        """
        payload = message['payload']
        headers = payload.get('headers', [])
        
        # Extract subject
        subject = ''
        for header in headers:
            if header['name'].lower() == 'subject':
                subject = header['value']
                break

        # Extract sender
        sender = ''
        for header in headers:
            if header['name'].lower() == 'from':
                sender = header['value']
                break

        # Extract date
        email_date = ''
        for header in headers:
            if header['name'].lower() == 'date':
                email_date = header['value']
                break
        
        # Function to decode part body
        def get_part_body(part):
            if 'body' in part and 'data' in part['body']:
                data = part['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
            return ''
        
        # Function to get part content type
        def get_part_content_type(part):
            for header in part.get('headers', []):
                if header['name'].lower() == 'content-type':
                    value = header['value'].lower()
                    if 'text/plain' in value:
                        return 'text/plain'
                    elif 'text/html' in value:
                        return 'text/html'
            return None
        
        # Extract body content
        plain_body = ''
        html_body = ''
        
        # Check if message has parts
        if 'parts' in payload:
            for part in payload['parts']:
                content_type = get_part_content_type(part)
                
                if content_type == 'text/plain':
                    plain_body += get_part_body(part)
                elif content_type == 'text/html':
                    html_body += get_part_body(part)
                    
                # Handle nested parts (for multipart/alternative)
                if 'parts' in part:
                    for nested_part in part['parts']:
                        nested_content_type = get_part_content_type(nested_part)
                        
                        if nested_content_type == 'text/plain':
                            plain_body += get_part_body(nested_part)
                        elif nested_content_type == 'text/html':
                            html_body += get_part_body(nested_part)
        else:
            # If no parts, try to get body directly
            body_data = payload.get('body', {}).get('data')
            if body_data:
                content_type = get_part_content_type(payload)
                body_text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                
                if content_type == 'text/plain':
                    plain_body = body_text
                elif content_type == 'text/html':
                    html_body = body_text
                else:
                    # If content type is not specified, assume plain text
                    plain_body = body_text
        
        return {
            'subject': subject,
            'sender': sender,
            'plain_body': plain_body,
            'html_body': html_body,
            'date': email_date,
        }

