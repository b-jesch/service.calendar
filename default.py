# -*- encoding: utf-8 -*-
from __future__ import print_function
import datetime

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

def main(mode=None, handle=None):

    if mode == 'require_oauth_key':
        Calendar().require_credentials(Calendar().CLIENT_CREDENTIALS, True)
        tools.writeLog('new credentials successfull received and stored', xbmc.LOGDEBUG)
        tools.Notify().notify(__LS__(30010), __LS__(30073))

    elif mode == 'check_mailsettings':
        mail = SMTPMail()
        try:
            mail.checkproperties()
            mail.sendmail(__LS__(30074) % (__LS__(30010), tools.release().hostname), __LS__(30075))
            tools.writeLog('mail delivered', xbmc.LOGNOTICE)
            tools.dialogOK(__LS__(30010), __LS__(30076) % (mail.smtp_client['recipient']))
        except mail.SMPTMailInvalidOrMissingParameterException, e:
            tools.writeLog('mail could not delivered, check your addon settings: %s' % (e.message), xbmc.LOGERROR)
            tools.dialogOK(__LS__(30010), __LS__(30077) % (mail.smtp_client['recipient']))
        except mail.SMTPMailNotDeliveredException, e:
            tools.writeLog('mail could not delivered, check your addon settings: $s' % (e.message), xbmc.LOGERROR)
            tools.dialogOK(__LS__(30010), __LS__(30077) % (mail.smtp_client['recipient']))

    elif mode == 'guitest':
        Popup = xbmcgui.WindowXMLDialog(__xml__, __path__)
        Popup.doModal()
        del Popup

    elif mode == 'getcontent':
        """
        Shows basic usage of the Google Calendar API.

        Creates a Google Calendar API service object and outputs a list of the next
        10 events on the user's calendar.
        """
        cal = Calendar()

        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        eventsResult = cal.service.events().list(
            calendarId='primary', timeMin=now, maxResults=30, singleEvents=True,
            orderBy='startTime').execute()
        events = eventsResult.get('items', [])
        cal.build_sheet(events, handle)

    else:
        pass

if __name__ == '__main__':

    action = None
    _addonHandle = None

    arguments = sys.argv
    if len(arguments) > 1:
        if arguments[0][0:6] == 'plugin':               # calling as plugin path
            _addonHandle = int(arguments[1])
            arguments.pop(0)
            arguments[1] = arguments[1][1:]

        params = tools.ParamsToDict(arguments[1])
        action = params.get('action', '')

    try:
        if action is not None:
            main(mode=action, handle=_addonHandle)
        else:
            main(mode='guitest')

    except Calendar.oAuthMissingSecretFile, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30070), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
    except Calendar.oAuthMissingCredentialsFile, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30072), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)
    except Calendar.oAuthIncomplete, e:
        tools.writeLog(e.message, xbmc.LOGERROR)
        tools.Notify().notify(__LS__(30010), __LS__(30071), icon=xbmcgui.NOTIFICATION_ERROR, repeat=True)