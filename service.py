# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil import relativedelta
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.googleCalendar import Calendar
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as t
import resources.lib.notification as DKT

__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__icon__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'skins', 'Default', 'media', 'icon.png')
__icon2__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'skins', 'Default', 'media', 'icon_alert.png')
__profiles__ = __addon__.getAddonInfo('profile')
__LS__ = __addon__.getLocalizedString

TEMP_STORAGE_CALENDARS = os.path.join(xbmc.translatePath(__profiles__), 'calendars.json')
TEMP_STORAGE_EVENTS = os.path.join(xbmc.translatePath(__profiles__), 'events.json')

if t.getAddonSetting('show_onstart', sType=t.BOOL):
    xbmcgui.Window(10000).setProperty('reminders', '1')
else:
    xbmcgui.Window(10000).setProperty('reminders', '0')

_cycle = 0

try:
    googlecal = Calendar()
    while xbmcgui.Window(10000).getProperty('reminders') == '1':
        if not os.path.exists(TEMP_STORAGE_EVENTS) or (int(time.time()) - os.path.getmtime(TEMP_STORAGE_EVENTS) > 300):

            # temporary calendar storage not exists or last download is older then 300 secs
            # refresh calendar and store
            t.writeLog('establish online connection to google calendar')
            now = datetime.utcnow().isoformat() + 'Z'
            timemax = (datetime.utcnow() + relativedelta.relativedelta(months=t.getAddonSetting('timemax', sType=t.NUM))).isoformat() + 'Z'
            googlecal.establish()
            cals = googlecal.get_calendarIdFromSetup(TEMP_STORAGE_CALENDARS)
            googlecal.get_events(TEMP_STORAGE_EVENTS, TEMP_STORAGE_CALENDARS, now, timemax, maxResult=30, calendars=cals)
        else:
            t.writeLog('getting calendar events from local storage')

        with open(TEMP_STORAGE_EVENTS, 'r') as filehandle: events = json.load(filehandle)

        _ev_count = 1
        for event in events:
            _ev = googlecal.prepare_events(event)
            t.Notify().notify('%s %s %s' % (_ev['timestamps'], __LS__(30145), _ev['shortdate']), _ev['summary'], icon=__icon__)
            _ev_count += 1
            xbmc.Monitor().waitForAbort(7)
            if _ev_count > t.getAddonSetting('numreminders', sType=t.NUM) or xbmcgui.Window(10000).getProperty('reminders') != '1': break

        if events and _cycle > 0:
            DialogKT = DKT.DialogKaiToast.createDialogKaiToast()
            DialogKT.label_1 = __LS__(30019)
            DialogKT.label_2 = __LS__(30018)
            DialogKT.icon = __icon2__
            DialogKT.show()
            xbmc.Monitor().waitForAbort(t.getAddonSetting('lastnoticeduration', sType=t.NUM))
            DialogKT.close()

        xbmc.Monitor().waitForAbort(t.getAddonSetting('interval', sType=t.NUM, multiplicator=60))
        _cycle += 1

except SMTPMail.SMPTMailInvalidOrMissingParameterException, e:
    t.writeLog(e.message, xbmc.LOGERROR)
    t.dialogOK(__LS__(30010), __LS__(30078))
except SMTPMail.SMTPMailNotDeliveredException, e:
    t.writeLog(e.message, xbmc.LOGERROR)
    t.dialogOK(__LS__(30010), __LS__(30077) % (SMTPMail.smtp_client['recipient']))

t.writeLog('Notification service finished', xbmc.LOGNOTICE)