# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil import relativedelta
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.googleCalendar import Calendar
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as tools
import resources.lib.notification as DKT

__addon__ = xbmcaddon.Addon()
__path__ = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))
__profiles__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
__icon__ = os.path.join(__path__, 'resources', 'skins', 'Default', 'media', 'icon.png')
__icon2__ = os.path.join(__path__, 'resources', 'skins', 'Default', 'media', 'icon_alert.png')
__LS__ = __addon__.getLocalizedString

TEMP_STORAGE_CALENDARS = os.path.join(__profiles__, 'calendars.json')
TEMP_STORAGE_NOTIFICATIONS = os.path.join(__profiles__, 'notifications.json')

if tools.getAddonSetting('show_onstart', sType=tools.BOOL):
    xbmcgui.Window(10000).setProperty('reminders', '1')
else:
    xbmcgui.Window(10000).setProperty('reminders', '0')

_cycle = 0

try:
    googlecal = Calendar()
    while xbmcgui.Window(10000).getProperty('reminders') == '1':
        now = datetime.utcnow().isoformat() + 'Z'
        timemax = (datetime.utcnow() + relativedelta.relativedelta(months=tools.getAddonSetting('timemax', sType=tools.NUM))).isoformat() + 'Z'
        events = googlecal.get_events(TEMP_STORAGE_NOTIFICATIONS, now, timemax, maxResult=30,
                                      calendars=googlecal.get_calendarIdFromSetup('notifications'), evtype='notification')

        _ev_count = 1
        for event in events:
            event = googlecal.prepareForAddon(event)
            tools.Notify().notify('%s %s %s' % (event['timestamps'], __LS__(30145), event['shortdate']),
                                  event['summary'] or event['description'].splitlines()[0], icon=__icon__)
            _ev_count += 1
            xbmc.Monitor().waitForAbort(7)
            if _ev_count > tools.getAddonSetting('numreminders', sType=tools.NUM) or xbmcgui.Window(10000).getProperty('reminders') != '1': break

        if events and _cycle > 0 and _cycle < tools.getAddonSetting('cycles', sType=tools.NUM):
            DialogKT = DKT.DialogKaiToast.createDialogKaiToast()
            DialogKT.label_1 = __LS__(30019)
            DialogKT.label_2 = __LS__(30018)
            DialogKT.icon = __icon2__
            DialogKT.show()
            xbmc.Monitor().waitForAbort(tools.getAddonSetting('lastnoticeduration', sType=tools.NUM))
            DialogKT.close()

        _cycle += 1
        if _cycle >= tools.getAddonSetting('cycles', sType=tools.NUM):
            tools.writeLog('max count of reminder cycles reached, stop notifications')
            break
        xbmc.Monitor().waitForAbort(tools.getAddonSetting('interval', sType=tools.NUM, multiplicator=60))


except SMTPMail.SMPTMailParameterException as e:
    tools.writeLog(e, xbmc.LOGERROR)
    tools.Notify().notify(__LS__(30010), __LS__(30078), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
except SMTPMail.SMTPMailNotDeliveredException as e:
    tools.writeLog(e, xbmc.LOGERROR)
    tools.dialogOK(__LS__(30010), __LS__(30077) % (SMTPMail.smtp_client['recipient']))

tools.writeLog('Notification service finished', xbmc.LOGINFO)