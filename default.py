# -*- encoding: utf-8 -*-
from __future__ import print_function
import datetime

import resources.lib.tools as tools
from resources.lib.googleCalendar import Calendar

import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('id')
__path__ = __addon__.getAddonInfo('path')
__profiles__ = __addon__.getAddonInfo('profile')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString


def getsettings():

    tools.getAddonSetting()

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
    else:
        cal.build_sheet(events)

if __name__ == '__main__':
    main()