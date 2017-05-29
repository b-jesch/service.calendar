# -*- encoding: utf-8 -*-
from datetime import datetime
import json
import os
import time

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.googleCalendar import Calendar
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as tools
import resources.lib.notification as DKT

__addon__ = xbmcaddon.Addon()
__path__ = __addon__.getAddonInfo('path')
__icon__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'skins', 'Default', 'media', 'icon.png')
__icon2__ = os.path.join(xbmc.translatePath(__path__), 'resources', 'skins', 'Default', 'media', 'icon_alert.png')
__profiles__ = __addon__.getAddonInfo('profile')
__LS__ = __addon__.getLocalizedString

TEMP_STORAGE_EVENTS = os.path.join(xbmc.translatePath(__profiles__), 'events.json')

if tools.getAddonSetting('show_onstart', sType=tools.BOOL):
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
            tools.writeLog('establish online connection to google calendar')
            now = datetime.utcnow().isoformat() + 'Z'
            googlecal.establish()
            googlecal.get_events(TEMP_STORAGE_EVENTS, timeMin=now, maxResult=30)
        else:
            tools.writeLog('getting calendar events from local storage')

        with open(TEMP_STORAGE_EVENTS, 'r') as filehandle: events = json.load(filehandle)

        _ev_count = 1
        for event in events:
            _ev = googlecal.prepare_events(event)
            tools.Notify().notify('%s %s %s' % (_ev['timestamps'], __LS__(30145), _ev['shortdate']), _ev['summary'], icon=__icon__)
            _ev_count += 1
            xbmc.Monitor().waitForAbort(7)
            if _ev_count > tools.getAddonSetting('numreminders', sType=tools.NUM) or xbmcgui.Window(10000).getProperty('reminders') != '1': break

        if events and _cycle > 0:
            DialogKT = DKT.DialogKaiToast.createDialogKaiToast()
            DialogKT.label_1 = __LS__(30019)
            DialogKT.label_2 = __LS__(30018)
            DialogKT.icon = __icon2__
            DialogKT.show()
            xbmc.Monitor().waitForAbort(5)
            DialogKT.close()

        xbmc.Monitor().waitForAbort(tools.getAddonSetting('interval', sType=tools.NUM, multiplicator=60))
        _cycle += 1

except SMTPMail.SMPTMailInvalidOrMissingParameterException, e:
    tools.writeLog(e.message, xbmc.LOGERROR)
    tools.dialogOK(__LS__(30010), __LS__(30078))
except SMTPMail.SMTPMailNotDeliveredException, e:
    tools.writeLog(e.message, xbmc.LOGERROR)
    tools.dialogOK(__LS__(30010), __LS__(30077) % (SMTPMail.smtp_client['recipient']))

tools.writeLog('Notification service finished', xbmc.LOGNOTICE)