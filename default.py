# -*- encoding: utf-8 -*-
from __future__ import print_function
from datetime import datetime
from dateutil import relativedelta
import time

import sys
import os

import resources.lib.tools as tools
from resources.lib.googleCalendar import Calendar
from resources.lib.simplemail import SMTPMail

import xbmc
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('id')
__path__ = __addon__.getAddonInfo('path')
__profiles__ = __addon__.getAddonInfo('profile')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__xml__ = xbmc.translatePath('special://skin').split(os.sep)[-2] + '.calendar.xml'

if not os.path.exists(xbmc.translatePath(__profiles__)): os.makedirs(xbmc.translatePath(__profiles__))

TEMP_STORAGE_EVENTS = os.path.join(xbmc.translatePath(__profiles__), 'events.json')
TEMP_STORAGE_CALENDARS = os.path.join(xbmc.translatePath(__profiles__), 'calendars.json')
TEMP_STORAGE_COLORS = os.path.join(xbmc.translatePath(__profiles__), 'colors.json')

class FileNotFoundException(Exception):
    pass

def main(mode=None, handle=None, content=None):

    if mode == 'require_oauth_key':
        Calendar().require_credentials(Calendar().CLIENT_CREDENTIALS, require_from_setup=True)
        tools.writeLog('new credentials successfull received and stored', xbmc.LOGDEBUG)
        tools.Notify().notify(__LS__(30010), __LS__(30073))

    elif mode == 'reenter_oauth_key':
        Calendar().require_credentials(Calendar().CLIENT_CREDENTIALS, require_from_setup=True, reenter='kb')
        tools.writeLog('new credentials successfull received and stored', xbmc.LOGDEBUG)
        tools.Notify().notify(__LS__(30010), __LS__(30073))

    elif mode == 'load_oauth_key':
        Calendar().require_credentials(Calendar().CLIENT_CREDENTIALS, require_from_setup=True, reenter='file')
        tools.writeLog('new credentials successfull received and stored', xbmc.LOGDEBUG)
        tools.Notify().notify(__LS__(30010), __LS__(30073))

    elif mode == 'check_mailsettings':
        mail = SMTPMail()
        mail.checkproperties()
        mail.sendmail(__LS__(30074) % (__LS__(30010), tools.release().hostname), __LS__(30075))
        tools.writeLog('mail delivered', xbmc.LOGNOTICE)
        tools.dialogOK(__LS__(30010), __LS__(30076) % (mail.smtp_client['recipient']))


    elif mode == 'abort_reminders':
        tools.writeLog('abort notification service by setup', xbmc.LOGNOTICE)
        xbmcgui.Window(10000).setProperty('reminders', '0')

    elif mode == 'gui':
        try:
            Popup = xbmcgui.WindowXMLDialog(__xml__, __path__)
        except RuntimeError, e:
            raise FileNotFoundException(e.message)

        Popup.doModal()
        del Popup

    elif mode == 'set_calendars':
        googlecal = Calendar()
        if not os.path.exists(TEMP_STORAGE_CALENDARS) or (int(time.time()) - os.path.getmtime(TEMP_STORAGE_CALENDARS) > 300):
            # temporary calendar storage not exists or last download is older then 300 secs
            # refresh calendar module and store
            tools.writeLog('establish online connection to google calendar')
            googlecal.establish()
            googlecal.set_calendars(TEMP_STORAGE_CALENDARS)

        cals = googlecal.get_calendars(TEMP_STORAGE_CALENDARS)
        _list = []
        for cal in cals:
            _list.append(cal.get('summaryOverride', cal.get('summary', 'primary')))
            # set primary calendar as default calendar
            if cal.get('primary', False): default = cal.get('summaryOverride', cal.get('summary', 'primary'))
        dialog = xbmcgui.Dialog()
        _idx = dialog.multiselect(__LS__(30091), _list)
        if _idx is not None:
            __addon__.setSetting('calendars', ', '.join(_list[i] for i in _idx))
        else:
            __addon__.setSetting('calendars', default)

    elif mode == 'getcontent':
        googlecal = Calendar()
        if  not os.path.exists(TEMP_STORAGE_EVENTS) or (int(time.time()) - os.path.getmtime(TEMP_STORAGE_EVENTS) > 300):
            tools.writeLog('establish online connection to google calendar')
            now = datetime.utcnow().isoformat() + 'Z'
            max = (datetime.utcnow() + relativedelta.relativedelta(months=tools.getAddonSetting('timemax', sType=tools.NUM))).isoformat() + 'Z'
            googlecal.establish()
            cals = googlecal.get_calendarIdFromSetup(TEMP_STORAGE_CALENDARS)
            googlecal.get_events(TEMP_STORAGE_EVENTS, timeMin=now, timeMax=max, maxResult=30, calendars=cals)
        else:
            tools.writeLog('getting calendar content from local storage')

        googlecal.build_sheet(handle, TEMP_STORAGE_EVENTS, content)

    else:
        pass

if __name__ == '__main__':

    action = None
    content = None
    _addonHandle = None

    arguments = sys.argv
    if len(arguments) > 1:
        if arguments[0][0:6] == 'plugin':               # calling as plugin path
            _addonHandle = int(arguments[1])
            arguments.pop(0)
            arguments[1] = arguments[1][1:]

        params = tools.ParamsToDict(arguments[1])
        action = params.get('action', '')
        content = params.get('content', '')

    tools.writeLog('action is %s' % (action), xbmc.LOGNOTICE)
    try:
        if action is not None:
            main(mode=action, handle=_addonHandle, content=content)
        else:
            main(mode='gui')

    except FileNotFoundException, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30079))
    except SMTPMail.SMPTMailInvalidOrMissingParameterException, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.dialogOK(__LS__(30010), __LS__(30078))
    except SMTPMail.SMTPMailNotDeliveredException, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.dialogOK(__LS__(30010), __LS__(30077) % (SMTPMail.smtp_client['recipient']))
    except Calendar.oAuthMissingSecretFile, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30070), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
    except Calendar.oAuthMissingCredentialsFile, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30072), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
    except Calendar.oAuthIncomplete, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30071), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
    except Calendar.oAuthFlowExchangeError, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.dialogOK(__LS__(30010), __LS__(30103))