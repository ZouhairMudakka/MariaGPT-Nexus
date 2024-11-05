from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.settings import settings
import os
import pickle
from typing import List, Dict, Any
import datetime

class GoogleDocsManager:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive.file',           # Access files created by app
            'https://www.googleapis.com/auth/documents.readonly',   # Read-only access to Docs
            'https://www.googleapis.com/auth/spreadsheets.readonly',# Read-only access to Sheets
            'https://www.googleapis.com/auth/presentations.readonly',# Read-only access to Slides
            'https://www.googleapis.com/auth/calendar.readonly',    # Read-only access to Calendar
            'https://www.googleapis.com/auth/calendar'              # Full access to Calendar
        ]
        self.creds = None
        self.docs_service = None
        self.sheets_service = None
        self.slides_service = None
        self.drive_service = None
        self.calendar_service = None
        self.authenticate()

    def authenticate(self):
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'multiagent_demo_credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        self.slides_service = build('slides', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
        
    def get_folder_contents(self, folder_id):
        """Get all files in a specific Google Drive folder"""
        try:
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents",
                fields="files(id, name, mimeType)"
            ).execute()
            return results.get('files', [])
        except Exception as e:
            print(f"Error accessing folder: {str(e)}")
            return []
            
    def get_document_content(self, doc_id):
        """Get content from a Google Doc"""
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            content = ''
            for elem in document.get('body').get('content'):
                if 'paragraph' in elem:
                    for para_elem in elem.get('paragraph').get('elements'):
                        if 'textRun' in para_elem:
                            content += para_elem.get('textRun').get('content')
            return content
        except Exception as e:
            print(f"Error fetching Google Doc: {str(e)}")
            return None
            
    def get_spreadsheet_content(self, sheet_id):
        """Get content from a Google Sheet"""
        try:
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=sheet_id, 
                includeGridData=True
            ).execute()
            content = []
            for sheet in spreadsheet.get('sheets', []):
                sheet_name = sheet['properties']['title']
                data = sheet.get('data', [])
                if data:
                    rows = []
                    for row in data[0].get('rowData', []):
                        row_data = []
                        for cell in row.get('values', []):
                            row_data.append(cell.get('formattedValue', ''))
                        rows.append(' | '.join(filter(None, row_data)))
                    content.append(f"Sheet: {sheet_name}\n" + '\n'.join(rows))
            return '\n\n'.join(content)
        except Exception as e:
            print(f"Error fetching Google Sheet: {str(e)}")
            return None
            
    def get_presentation_content(self, presentation_id):
        """Get content from Google Slides"""
        try:
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()
            content = []
            for slide in presentation.get('slides', []):
                slide_content = []
                for element in slide.get('pageElements', []):
                    if 'shape' in element and 'text' in element['shape']:
                        for textElement in element['shape']['text'].get('textElements', []):
                            if 'textRun' in textElement:
                                slide_content.append(textElement['textRun']['content'])
                content.append(' '.join(slide_content))
            return '\n\n'.join(content)
        except Exception as e:
            print(f"Error fetching Google Slides: {str(e)}")
            return None

    def test_connection(self) -> bool:
        """Test Google Drive connection"""
        try:
            if not self.drive_service:
                self.authenticate()
            results = self.drive_service.files().list(
                pageSize=1, fields="files(id, name)").execute()
            return True
        except Exception as e:
            print(f"Google Drive connection error: {str(e)}")
            return False

    def get_available_slots(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Fetch available appointment slots from the calendar."""
        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            future = (datetime.datetime.utcnow() + 
                     datetime.timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events = self.calendar_service.events().list(
                calendarId=settings.google_settings['calendar_id'],
                timeMin=now,
                timeMax=future,
                singleEvents=True,
                orderBy='startTime',
                showDeleted=False,
                q='Available'  # Match your calendar's naming convention
            ).execute()
            
            available_slots = []
            for event in events.get('items', []):
                if event.get('status') != 'cancelled':
                    slot = {
                        'id': event['id'],
                        'start': event['start'].get('dateTime'),
                        'end': event['end'].get('dateTime'),
                        'summary': event.get('summary', 'Available'),
                    }
                    available_slots.append(slot)
            
            return available_slots
            
        except Exception as e:
            print(f"Error fetching available slots: {str(e)}")
            return []

    def book_appointment_slot(self, event_id: str, attendee_email: str, 
                         meeting_purpose: str) -> bool:
        """Book a specific appointment slot."""
        try:
            event = self.calendar_service.events().get(
                calendarId=settings.google_settings['calendar_id'],
                eventId=event_id
            ).execute()
            
            # Update event details
            event['summary'] = f"Meeting: {meeting_purpose}"
            event['attendees'] = [{'email': attendee_email}]
            event['status'] = 'confirmed'
            
            updated_event = self.calendar_service.events().update(
                calendarId=settings.google_settings['calendar_id'],
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Error booking appointment slot: {str(e)}")
            return False