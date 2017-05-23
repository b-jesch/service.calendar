# -*- encoding: utf-8 -*-
from __future__ import print_function
from datetime import datetime
import time

import sys
import os
import json

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


    elif mode == 'service':
        Popup = xbmcgui.WindowXMLDialog(__xml__, __path__)
        if tools.getAddonSetting('show_onstart', sType=tools.BOOL):
            _st = tools.getAddonSetting('showtime', sType=tools.NUM)
            tools.writeLog('show calendar for %s seconds' % (_st), xbmc.LOGNOTICE)
            Popup.show()
            xbmc.Monitor().waitForAbort(_st)
            Popup.close()
        else:
            Popup.doModal()
        del Popup

    elif mode == 'gui':
        Popup = xbmcgui.WindowXMLDialog(__xml__, __path__)
        Popup.doModal()
        del Popup

    elif mode == 'getcontent':
        """
        Shows basic usage of the Google Calendar API.

        Creates a Google Calendar API service object and outputs a list of the next
        10 events on the user's calendar.
        """
        googlecal = Calendar()
        if  not os.path.exists(TEMP_STORAGE_EVENTS) or (int(time.time()) - os.path.getmtime(TEMP_STORAGE_EVENTS) > 300):

            # temporary calendar storage not exists or last modification is older then 300 secs
            # refresh calendar and store
            tools.writeLog('establish online connection to google calendar')
            now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
            googlecal.establish()

            cal_list = googlecal.service.calendarList().list().execute()
            cals = cal_list.get('items', [])
            with open(TEMP_STORAGE_CALENDARS, 'w') as filehandle: json.dump(cals, filehandle)

            cal_events = googlecal.service.events().list(calendarId='primary', timeMin=now, maxResults=30, singleEvents=True, orderBy='startTime').execute()
            events = cal_events.get('items', [])

            with open(TEMP_STORAGE_EVENTS, 'w') as filehandle:  json.dump(events, filehandle)
        else:
            tools.writeLog('getting calendar events from local store')

        with open(TEMP_STORAGE_EVENTS, 'r') as filehandle: events = json.load(filehandle)
        googlecal.build_sheet(handle, events, content)

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