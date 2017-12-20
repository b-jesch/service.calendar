# -*- encoding: utf-8 -*-
from __future__ import print_function
from datetime import datetime
from dateutil import relativedelta

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
TEMP_STORAGE_NOTIFICATIONS = os.path.join(xbmc.translatePath(__profiles__), 'notifications.json')

if not (xbmcgui.Window(10000).getProperty('calendar_month') or xbmcgui.Window(10000).getProperty('calendar_year')):
    xbmcgui.Window(10000).setProperty('calendar_month', str(datetime.today().month))
    xbmcgui.Window(10000).setProperty('calendar_year', str(datetime.today().year))
    _header = '%s %s' % (__LS__(30119 + datetime.today().month), datetime.today().year)
    xbmcgui.Window(10000).setProperty('calendar_header', _header)

class FileNotFoundException(Exception):
    pass

def calc_boundaries(direction):
    sheet_m = int(xbmcgui.Window(10000).getProperty('calendar_month')) + direction
    sheet_y = int(xbmcgui.Window(10000).getProperty('calendar_year'))

    if sheet_m < 1:
        sheet_m = 12
        sheet_y -= 1
    elif sheet_m > 12:
        sheet_m = 1
        sheet_y += 1

    if sheet_y == datetime.today().year:
        if sheet_m < datetime.today().month or sheet_m > datetime.today().month + tools.getAddonSetting('timemax', sType=tools.NUM):
            tools.writeLog('prev/next month outside boundary')
            return
    else:
        if sheet_m + 12 > datetime.today().month + tools.getAddonSetting('timemax', sType=tools.NUM):
            tools.writeLog('prev/next month outside boundary')
            return

    xbmcgui.Window(10000).setProperty('calendar_month', str(sheet_m))
    xbmcgui.Window(10000).setProperty('calendar_year', str(sheet_y))
    _header = '%s %s' % (__LS__(30119 + sheet_m), sheet_y)
    xbmcgui.Window(10000).setProperty('calendar_header', _header)

def set_localsetting(setting):
    googlecal = Calendar()
    cals = googlecal.get_calendars()

    _list = []
    for cal in cals:
        _list.append(cal.get('summaryOverride', cal.get('summary', 'primary')))
    dialog = xbmcgui.Dialog()
    _idx = dialog.multiselect(__LS__(30091), _list)
    if _idx is not None:
        __addon__.setSetting(setting, ', '.join(_list[i] for i in _idx))

def controller(mode=None, handle=None, content=None, eventId=None):
    now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
    timemax = (datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) +
               relativedelta.relativedelta(months=tools.getAddonSetting('timemax', sType=tools.NUM))).isoformat() + 'Z'

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

    elif mode == 'load_glotz_key':
        glotz_apikey = tools.dialogFile(__LS__(30089))
        if glotz_apikey != '':
            tools.setAddonSetting('glotz_apikey', glotz_apikey)
            tools.writeLog('API key for glotz.info successfull stored')
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

    elif mode == 'set_calendars':
        set_localsetting('calendars')
        googlecal = Calendar()
        googlecal.get_events(TEMP_STORAGE_EVENTS, now, timemax, maxResult=30, calendars=googlecal.get_calendarIdFromSetup('calendars'))

    elif mode == 'set_notifications':
        set_localsetting('notifications')
        googlecal = Calendar()
        googlecal.get_events(TEMP_STORAGE_NOTIFICATIONS, now, timemax, maxResult=30, calendars=googlecal.get_calendarIdFromSetup('notifications'))

    elif mode == 'getcontent':
        googlecal = Calendar()
        googlecal.build_sheet(handle, TEMP_STORAGE_EVENTS, content, now, timemax, maxResult=30, calendars=googlecal.get_calendarIdFromSetup('calendars'))

    elif mode == 'getinfo' and eventId != '':
        googlecal = Calendar()
        events = eventId.strip(' ').split(' ')
        _msg = ''
        for event in events:
            _ev = googlecal.get_event(event, TEMP_STORAGE_EVENTS)
            _mev = googlecal.prepareForAddon(_ev, optTimeStamps=True)
            _time = '' if _mev.get('range', '') == '' else '[B]%s[/B]: ' % (_mev.get('range'))
            _msg += '%s%s[CR]%s[CR][CR]' % (_time, _mev.get('summary', ''),
                                            _mev.get('description', False) or _mev.get('location', False) or __LS__(30093))
        tools.dialogOK('%s %s %s' % (__LS__(30109), __LS__(30145), _mev.get('shortdate', '')), _msg)

    elif mode == 'prev':
        calc_boundaries(-1)

    elif mode == 'next':
        calc_boundaries(1)

    # this is the real controller bootstrap
    elif mode == 'gui':
        try:
            Popup = xbmcgui.WindowXMLDialog(__xml__, __path__)
            Popup.doModal()
            del Popup
        except RuntimeError, e:
            raise FileNotFoundException('%s: %s' % (e.message, __xml__))
    else:
        pass

if __name__ == '__main__':

    action = None
    content = None
    eventId = None
    _addonHandle = None

    arguments = sys.argv
    if len(arguments) > 1:
        if arguments[0][0:6] == 'plugin':               # calling as plugin path
            _addonHandle = int(arguments[1])
            arguments.pop(0)
            arguments[1] = arguments[1][1:]

        tools.writeLog('parameter hash: %s' % (str(arguments[1])), xbmc.LOGNOTICE)
        params = tools.ParamsToDict(arguments[1])
        action = params.get('action', '')
        content = params.get('content', '')
        eventId = params.get('id', '')

    # call the controller of MVC
    try:
        if action is not None:
            controller(mode=action, handle=_addonHandle, content=content, eventId=eventId)
        else:
            controller(mode='gui')

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