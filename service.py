# -*- encoding: utf-8 -*-

from datetime import datetime
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.googleCalendar import Calendar
import resources.lib.tools as tools

__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__profiles__ = __addon__.getAddonInfo('profile')

TEMP_STORAGE_EVENTS = os.path.join(xbmc.translatePath(__profiles__), 'events.json')

class FileNotFoundException(Exception):
    pass


def createWindow(label, left=0, top=0, width=1920, height=35):
    w_Id = xbmcgui.getCurrentWindowId()
    window = xbmcgui.Window(w_Id)
    res = window.getWidth()

    tools.writeLog('X-Resolution for ID %s: %s' % (w_Id, res))

    tc = xbmcgui.ControlGroup(left, top, res, height)
    window.addControl(tc)
    bc = xbmcgui.ControlImage(left, top, res, height, 'weekdays.png')
    window.addControl(bc)
    txtc = xbmcgui.ControlLabel(left + 20, top + 5, res - 40, height - 10, label, font='font25_title', textColor='FFFFFFFF')
    window.addControl(txtc)

    xbmc.Monitor().waitForAbort(20)
    window.removeControls([txtc, bc, tc])


googlecal = Calendar()
if not os.path.exists(TEMP_STORAGE_EVENTS) or (int(time.time()) - os.path.getmtime(TEMP_STORAGE_EVENTS) > 300):

    # temporary calendar storage not exists or last download is older then 300 secs
    # refresh calendar and store
    tools.writeLog('establish online connection to google calendar')
    now = datetime.utcnow().isoformat() + 'Z'
    googlecal.establish()
    googlecal.get_events(TEMP_STORAGE_EVENTS, timeMin=now, maxResult=30)
else:
    tools.writeLog('getting calendar events from local storage')

with open(TEMP_STORAGE_EVENTS, 'r') as filehandle: events = json.load(filehandle)

createWindow(0,0,1920,35)

'''
try:
    Popup = xbmcgui.WindowXMLDialog('ticker.xml', __path__)
except RuntimeError, e:
    raise FileNotFoundException(e.message)

Popup.doModal()
del Popup
'''