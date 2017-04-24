from __future__ import print_function

import datetime

from dateutil import parser
from resources.lib.googleCalendar import Calendar

def main():
    """
    Shows basic usage of the Google Calendar API.

    Creates a Google Calendar API service object and outputs a list of the next
    10 events on the user's calendar.
    """
    cal = Calendar()

    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    eventsResult = cal.service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    print (events)

    if not events:
        print('No upcoming events found.')
    for event in events:
        print (event)
        _start = event['start'].get('dateTime', event['start'].get('date'))
        # print (', '.join([parser.parse(_start).strftime('%d.%m.%Y %H:%M'), event.get('summary', ''), event.get('location', 'n.a.')]))

    # print (cal.get_color('1', scope='event'))

if __name__ == '__main__':
    main()