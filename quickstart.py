import os.path
import json
from datetime import datetime, timezone, timedelta, time
from dotenv import load_dotenv


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
load_dotenv()
CALENDAR_ID = os.getenv("CALENDAR_ID")

tz = timezone(timedelta(hours=5))

creds = None

if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
        token.write(creds.to_json())

service = build("calendar", "v3", credentials=creds)


def main(start, end):
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
    # Call the Calendar API
  start_dt = datetime.fromisoformat(start)
  end_dt = datetime.fromisoformat(end)

  start_local = start_dt.astimezone(tz)
  end_local = end_dt.astimezone(tz)

  day_start = datetime.combine(start_local.date(), time.min, tzinfo=tz)
  day_end = datetime.combine(end_local.date(), time.min, tzinfo=tz) + timedelta(days=1)

  print("Getting the events for the day:")
  events_result = (
      service.events()
      .list(
          calendarId="primary",
          timeMin=day_start.isoformat(),
          timeMax=day_end.isoformat(),
          maxResults=20,
          singleEvents=True,
          orderBy="startTime",
      )
      .execute()
  )
  events = events_result.get("items", [])

  if not events:
    return json.dumps({"status": "ok", "message": "No upcoming events"})

  # Prints the start and name of the next 10 events

  events = []

  for event in events_result.get("items", []):
    events.append({
      "title": event.get("summary", "no title"),
      "start": event["start"].get("dateTime", event["start"].get("date")),
      "end": event["end"].get("dateTime", event["end"].get("date")),
    })

  return json.dumps({"status": "ok", "events": events}, ensure_ascii=True)



def create_calendar_event(title, start, end):

  body = {
     "summary": title,
     "start": {"dateTime": start},
    "end": {"dateTime": end}
    }

  try:
     event = service.events().insert(calendarId=CALENDAR_ID, body=body).execute()
     
  except HttpError as error:
     return json.dumps({"status": "error", "message": f"{error}"})

  return json.dumps({"status": "created", "link": event.get("htmlLink")})
   


if __name__ == "__main__":
  print(create_calendar_event("test event", "2026-10-20T15:00:00+05:00", "2026-10-20T16:00:00+05:00"))