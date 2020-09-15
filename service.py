# -*- encoding: utf-8 -*-
from resources.lib.tools import *
from datetime import datetime
from dateutil import relativedelta
import os


from resources.lib.googleCalendar import Calendar
from resources.lib.simplemail import SMTPMail
import resources.lib.notification as DKT

__icon__ = os.path.join(PATH, 'resources', 'skins', 'Default', 'media', 'icon.png')
__icon2__ = os.path.join(PATH, 'resources', 'skins', 'Default', 'media', 'icon_alert.png')

TEMP_STORAGE_CALENDARS = os.path.join(PROFILES, 'calendars.json')
TEMP_STORAGE_NOTIFICATIONS = os.path.join(PROFILES, 'notifications.json')

if getAddonSetting('show_onstart', sType=BOOL):
    xbmcgui.Window(10000).setProperty('reminders', '1')
else:
    xbmcgui.Window(10000).setProperty('reminders', '0')

_cycle = 0

try:
    googlecal = Calendar()
    while xbmcgui.Window(10000).getProperty('reminders') == '1':
        now = datetime.utcnow().isoformat() + 'Z'
        timemax = (datetime.utcnow() + relativedelta.relativedelta(months=getAddonSetting('timemax', sType=NUM, isLabel=True))).isoformat() + 'Z'
        events = googlecal.get_events(TEMP_STORAGE_NOTIFICATIONS, now, timemax, maxResult=30,
                                      calendars=googlecal.get_calendarIdFromSetup('notifications'), evtype='notification')

        _ev_count = 1
        for event in events:
            event = googlecal.prepareForAddon(event)
            Notify().notify('%s %s %s' % (event['timestamps'], LS(30145), event['shortdate']),
                                  event['summary'] or event['description'].splitlines()[0], icon=__icon__)
            _ev_count += 1
            xbmc.Monitor().waitForAbort(7)
            if _ev_count > getAddonSetting('numreminders', sType=NUM) or xbmcgui.Window(10000).getProperty('reminders') != '1': break

        if events and 0 < _cycle < getAddonSetting('cycles', sType=NUM):
            DialogKT = DKT.DialogKaiToast.createDialogKaiToast()
            DialogKT.label_1 = LS(30019)
            DialogKT.label_2 = LS(30018)
            DialogKT.icon = __icon2__
            DialogKT.show()
            xbmc.Monitor().waitForAbort(getAddonSetting('lastnoticeduration', sType=NUM, isLabel=True))
            DialogKT.close()

        _cycle += 1
        if _cycle >= getAddonSetting('cycles', sType=NUM):
            writeLog('max count of reminder cycles reached, stop notifications')
            break
        xbmc.Monitor().waitForAbort(getAddonSetting('interval', sType=NUM, multiplicator=60, isLabel=True))

except TypeError as e:
    writeLog(e, xbmc.LOGERROR)
except SMTPMail.SMPTMailParameterException as e:
    writeLog(e, xbmc.LOGERROR)
    Notify().notify(LS(30010), LS(30078), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
except SMTPMail.SMTPMailNotDeliveredException as e:
    writeLog(e, xbmc.LOGERROR)
    dialogOK(LS(30010), LS(30077) % (SMTPMail.smtp_client['recipient']))

writeLog('Notification service finished', xbmc.LOGINFO)