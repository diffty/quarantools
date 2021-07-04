import pickle
import os
import sys
import datetime
import re
import json

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def auth():
    # Auth
    creds = None

    token_path = "creds/token_cal.pickle"
    creds_path = "creds/credentials.json"

    if not os.path.exists(creds_path):
        raise Exception("<!!> Creds JSON cannot be found in %s" % creds_path)

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "creds/credentials.json", SCOPES
            )

            creds = flow.run_console()
        
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return creds


def get_calendar_service(creds):
    service = build("calendar", "v3", credentials=creds)
    return service.events()


def convert_iso_datetime(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def main(calendar_id):
    creds = auth()
    cal_service = get_calendar_service(creds) 

    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    
    events_result = cal_service.list(
        calendarId=calendar_id,
        timeMin=now,
        maxResults=2,
        singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])

    curr_event = None
    next_event = None

    tz = datetime.datetime.now().astimezone().tzinfo 

    if convert_iso_datetime(events[0]["start"]["dateTime"]) > datetime.datetime.now(tz=tz):
        next_event = events[0]

    elif len(events) == 1:
        curr_event = events[0]

    elif len(events) == 2:
        curr_event = events[0]
        next_event = events[1]

    return curr_event, next_event


if __name__ == "__main__":
    main("3gnqq7o0srsodr775uolf16fg8@group.calendar.google.com")
