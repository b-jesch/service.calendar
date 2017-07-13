# -*- encoding: utf-8 -*-

from apiclient import discovery
from oauth2client import client
from oauth2client.file import Storage

import httplib2
import os
import operator
from resources.lib import tinyurl
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as t

import time
import calendar
from datetime import datetime
from dateutil import parser, relativedelta
import json

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('id')
__addonpath__ = __addon__.getAddonInfo('path')
__profiles__ = __addon__.getAddonInfo('profile')
__LS__ = __addon__.getLocalizedString
__icon__ = os.path.join(xbmc.translatePath(__addonpath__), 'resources', 'skins', 'Default', 'media', 'icon.png')
__symbolpath__ = os.path.join(xbmc.translatePath(__addonpath__), 'resources', 'skins', 'Default', 'media')
__cake__ = os.path.join(__symbolpath__, 'cake_2.png')

mail = SMTPMail()

class Calendar(object):

    class oAuthMissingSecretFile(Exception):
        pass

    class oAuthMissingCredentialsFile(Exception):
        pass

    class oAuthIncomplete(Exception):
        pass

    class oAuthFlowExchangeError(Exception):
        pass

    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/service.calendar.json

    CLIENTS_PATH = os.path.join(xbmc.translatePath(__profiles__), '_credentials')
    if not os.path.exists(CLIENTS_PATH): os.makedirs(CLIENTS_PATH)

    COLOR_PATH = os.path.join(xbmc.translatePath(__profiles__), '_colors')
    if not os.path.exists(COLOR_PATH): os.makedirs(COLOR_PATH)

    SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
    CLIENT_SECRET_FILE = os.path.join(xbmc.translatePath(__addonpath__), '_credentials', 'service.calendar.oauth.json')
    CLIENT_CREDENTIALS = os.path.join(CLIENTS_PATH, 'service.calendar.credits.json')
    APPLICATION_NAME = 'service.calendar'
    SHEET_ID = 30008

    TEMP_STORAGE_CALENDARS = os.path.join(xbmc.translatePath(__profiles__), 'calendars.json')

    def __init__(self):
        self.addtimestamps = t.getAddonSetting('additional_timestamps', sType=t.BOOL)

    def establish(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

    def get_credentials(self):
        if not os.path.isfile(self.CLIENT_SECRET_FILE):
            raise self.oAuthMissingSecretFile('missing %s' % (self.CLIENT_SECRET_FILE))

        storage = Storage(self.CLIENT_CREDENTIALS)
        credentials = storage.get()

        if not credentials or credentials.invalid:
            credentials = self.require_credentials(self.CLIENT_CREDENTIALS)

        return credentials

    def require_credentials(self, storage_path, require_from_setup=False, reenter=None):
        storage = Storage(storage_path)
        try:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES,
                                                  redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            flow.user_agent = self.APPLICATION_NAME

            auth_code = ''
            if reenter is None:
                auth_uri = tinyurl.create_one(flow.step1_get_authorize_url())

                if require_from_setup:
                    _dialog = __LS__(30082)
                else:
                    _dialog = '%s %s' % (__LS__(30081), __LS__(30082))

                if not t.dialogYesNo(__LS__(30080), _dialog):
                    raise self.oAuthIncomplete('oAuth2 flow aborted by user')
                t.dialogOK(__LS__(30080), __LS__(30083))

                mail.checkproperties()
                mail.sendmail(__LS__(30100) % (__addonname__), __LS__(30101) % (auth_uri))
                if not t.dialogYesNo(__LS__(30080), __LS__(30087)):
                    raise self.oAuthIncomplete('oAuth2 flow aborted by user')
                reenter = 'kb'

            if reenter == 'kb':
                auth_code = t.dialogKeyboard(__LS__(30084))
            elif reenter == 'file':
                auth_code = t.dialogFile(__LS__(30086))

            if auth_code == '':
                raise self.oAuthIncomplete('no key provided')

            credentials = flow.step2_exchange(auth_code)
            storage.put(credentials)
        except client.FlowExchangeError, e:
            raise self.oAuthFlowExchangeError(e.message)

        return credentials

    def get_events(self, storage, timeMin, timeMax, maxResult=30, calendars='primary'):
        if not os.path.exists(storage) or not t.lastmodified(storage, 60):
            t.writeLog('establish online connection for getting events')
            self.establish()

            events = []
            for cal in calendars:
                cal_events = self.service.events().list(calendarId=cal, timeMin=timeMin, timeMax=timeMax,
                                                        maxResults=maxResult, singleEvents=True,
                                                        orderBy='startTime').execute()
                _evs = cal_events.get('items', [])
                if _evs:
                    # set additional attributes
                    calColor = self.get_calendarBGcolorImage(cal)
                    for _ev in _evs:
                        _ts = parser.parse(_ev['start'].get('dateTime', _ev['start'].get('date', ''))).timetuple()

                        _ev.update({'timestamp': int(time.mktime(_ts))})
                        _ev.update({'icon': calColor})

                        gadget = _ev.get('gadget', None)
                        if gadget:
                            if gadget.get('preferences').get('goo.contactsEventType') == 'BIRTHDAY':
                                _ev.update({'specialicon': __cake__})
                    events.extend(_evs)

            events.sort(key=operator.itemgetter('timestamp'))
            with open(storage, 'w') as filehandle:  json.dump(events, filehandle)
        else:
            t.writeLog('getting events from local storage')
            with open(storage, 'r') as filehandle: events = json.load(filehandle)
        return events

    def get_event(self, eventId, storage):
        with open(storage, 'r') as filehandle: events = json.load(filehandle)
        for event in events:
            if event.get('id', '') == eventId: return event
        return False

    @classmethod
    def prepare_events(cls, event, timebase=datetime.now(), optTimeStamps=True):

        ev_item = {}

        _dt = parser.parse(event['start'].get('date', event['start'].get('dateTime')))
        _end = parser.parse(event['end'].get('dateTime', event['end'].get('date', '')))
        _tdelta = relativedelta.relativedelta(_end.date(), _dt.date())
        _range = 0 if event['start'].get('dateTime') else _tdelta.days

        ev_item.update({'allday': _range})
        ev_item.update({'id': event.get('id', '')})
        ev_item.update({'date': _dt})
        ev_item.update({'shortdate': _dt.strftime('%d.%m')})
        ev_item.update({'summary': event.get('summary', '')})
        ev_item.update({'description': event.get('description', None)})
        ev_item.update({'location': event.get('location', None)})
        ev_item.update({'icon': event.get('icon', '')})
        ev_item.update({'specialicon': event.get('specialicon', '')})

        if _range > 0:
            if _tdelta.months == 0 and _tdelta.weeks == 0 and _range == 1: ev_item.update({'range': __LS__(30111)})
            elif _tdelta.months == 0 and _tdelta.weeks == 0: ev_item.update({'range': __LS__(30112) % (_range)})
            elif _tdelta.months == 0 and _tdelta.weeks == 1: ev_item.update({'range': __LS__(30113)})
            elif _tdelta.months == 0 and _tdelta.weeks > 0: ev_item.update({'range': __LS__(30114) % (_tdelta.weeks)})
            elif _tdelta.months == 1: ev_item.update({'range': __LS__(30115)})
            elif _tdelta.months > 1: ev_item.update({'range': __LS__(30116) % (_tdelta.months)})
            else: ev_item.update({'range': __LS__(30117)})
        else:
            _end = parser.parse(event['end'].get('dateTime', ''))
            if _dt != _end:
                ev_item.update({'range': _dt.strftime('%H:%M') + ' - ' + _end.strftime('%H:%M')})
            else:
                ev_item.update({'range': _dt.strftime('%H:%M')})

        if optTimeStamps:
            t.writeLog('calculate additional timestamps')

            _tdelta = relativedelta.relativedelta(_dt.date(), timebase.date())
            if _tdelta.months == 0:
                if _tdelta.days == 0: ats = __LS__(30139)
                elif _tdelta.days == 1: ats = __LS__(30140)
                elif _tdelta.days == 2: ats = __LS__(30141)
                elif 3 <= _tdelta.days <= 6: ats = __LS__(30142) % (_tdelta.days)
                elif _tdelta.weeks == 1: ats = __LS__(30143)
                elif _tdelta.weeks > 1: ats = __LS__(30144) % (_tdelta.weeks)
                else: ats = __LS__(30117)
            elif _tdelta.months == 1: ats = __LS__(30146)
            else: ats = __LS__(30147) % (_tdelta.months)
            ev_item.update({'timestamps': ats})

        return ev_item

    def get_calendars(self):
        if not os.path.exists(self.TEMP_STORAGE_CALENDARS) or not t.lastmodified(self.TEMP_STORAGE_CALENDARS, 60):
            t.writeLog('establish online connection for getting calendars')
            self.establish()
            cal_list = self.service.calendarList().list().execute()
            cals = cal_list.get('items', [])
            with open(self.TEMP_STORAGE_CALENDARS, 'w') as filehandle: json.dump(cals, filehandle)
            return cals
        else:
            t.writeLog('getting calendars from local storage')
            with open(self.TEMP_STORAGE_CALENDARS, 'r') as filehandle: return json.load(filehandle)

    def get_calendarIdFromSetup(self, setting):
        calId = []
        _cals = t.getAddonSetting(setting).split(', ')
        if len(_cals) == 1 and _cals[0] == 'primary':
            calId.append('primary')
        else:
            cals = self.get_calendars()
            for cal in cals:
                if cal.get('summaryOverride', cal.get('summary', 'primary')) in _cals: calId.append(cal.get('id'))
        t.writeLog('getting cal ids from setup: %s' % (', '.join(calId)))
        return calId

    def get_calendarBGcolorImage(self, calendarId):
        cals = self.get_calendars()
        for cal in cals:
            if cal.get('id') == calendarId:
                return t.createImage(15, 40, cal.get('backgroundColor', '#808080'),
                                     os.path.join(self.COLOR_PATH, cal.get('backgroundColor', '#808080') + '.png'))

    def build_sheet(self, handle, storage, content, now, timemax, maxResult, calendars):
        self.sheet = []
        dom = 1
        _today = None
        _todayCID = 0
        _now = datetime.now()

        events = self.get_events(storage, now, timemax, maxResult, calendars)

        sheet_m = int(xbmcgui.Window(10000).getProperty('calendar_month'))
        sheet_y = int(xbmcgui.Window(10000).getProperty('calendar_year'))

        if sheet_m == datetime.today().month and sheet_y == datetime.today().year:
            _today = datetime.today().day

        start, sheets = calendar.monthrange(sheet_y, sheet_m)
        prolog = (parser.parse('%s/1/%s' % (sheet_m, sheet_y)) - relativedelta.relativedelta(days=start)).day
        epilog = 1

        for cid in xrange(0, 42):
            if cid < start or cid >= start + sheets:

                # daily sheets outside of actual month, set these to valid:0
                self.sheet.append({'cid': str(cid), 'valid': '0'})
                if cid < start:
                    self.sheet[cid].update(dom=str(prolog))
                    prolog += 1
                else:
                    self.sheet[cid].update(dom=str(epilog))
                    epilog += 1
                continue

            num_events = 0
            event_ids = ''
            allday = 0
            specialicon = ''

            for event in events:
                _ev = self.prepare_events(event, _now, optTimeStamps=False)

                if _ev['date'].day == dom and _ev['date'].month == sheet_m and _ev['date'].year == sheet_y:
                    event_ids += ' %s' % (_ev['id'])
                    num_events += 1
                    if _ev['allday'] > allday: allday = _ev['allday']
                    if _ev.get('specialicon', '') != '': specialicon = _ev.get('specialicon')

                if allday == 0: eventicon = os.path.join(__symbolpath__, 'eventmarker_1.png')
                elif allday == 1: eventicon = os.path.join(__symbolpath__, 'eventmarker_2.png')
                else: eventicon = os.path.join(__symbolpath__, 'eventmarker_3.png')

            self.sheet.append({'cid': cid, 'valid': '1', 'dom': str(dom)})
            if num_events > 0:
                self.sheet[cid].update(num_events=str(num_events), allday=allday, event_ids=event_ids,
                                       specialicon=specialicon, eventicon=eventicon)
            if _today == int(self.sheet[cid].get('dom')):
                self.sheet[cid].update(today='1')
                _todayCID = cid
            dom += 1

        if content == 'sheet':
            for cid in range(0, 42):
                cal_sheet = xbmcgui.ListItem(label=self.sheet[cid].get('dom'), label2=self.sheet[cid].get('num_events', '0'),
                                             iconImage=self.sheet[cid].get('eventicon', ''))
                cal_sheet.setProperty('valid', self.sheet[cid].get('valid', '0'))
                cal_sheet.setProperty('allday', str(self.sheet[cid].get('allday', 0)))
                cal_sheet.setProperty('today', self.sheet[cid].get('today', '0'))
                cal_sheet.setProperty('ids', self.sheet[cid].get('event_ids', ''))
                cal_sheet.setProperty('specialicon', self.sheet[cid].get('specialicon', ''))
                xbmcplugin.addDirectoryItem(handle, url='', listitem=cal_sheet)
            # set at least focus to the current day
            xbmc.executebuiltin('Control.SetFocus(%s, %s)' % (self.SHEET_ID, _todayCID))

        elif content == 'eventlist':
            for event in events:
                _ev = self.prepare_events(event, _now, optTimeStamps=self.addtimestamps)
                if _ev['date'].month >= sheet_m and _ev['date'].year >= sheet_y:
                    if self.addtimestamps:
                        li = xbmcgui.ListItem(label=_ev['shortdate'] + ' - ' + _ev['timestamps'], label2=_ev['summary'],
                                              iconImage=_ev['icon'])
                    else:
                        li = xbmcgui.ListItem(label=_ev['shortdate'], label2=_ev['summary'], iconImage=_ev['icon'])
                    li.setProperty('id', _ev.get('id', ''))
                    li.setProperty('range', _ev.get('range', ''))
                    li.setProperty('allday', str(_ev.get('allday', 0)))
                    li.setProperty('description', _ev.get('description') or _ev.get('location'))
                    xbmcplugin.addDirectoryItem(handle, url='', listitem=li)

        xbmcplugin.endOfDirectory(handle, updateListing=True)
