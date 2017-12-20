# -*- encoding: utf-8 -*-

from googleapiclient import discovery
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
from datetime import datetime, timedelta
from dateutil import parser, relativedelta
import json
import urllib
import sys

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
    GLOTZ_URL = 'https://www.glotz.info/v2/user/calendar/%s' % (t.getAddonSetting('glotz_apikey'))

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

    def get_events(self, storage, timeMin, timeMax, maxResult=30, calendars='primary', evtype='default'):
        if not os.path.exists(storage) or not t.lastmodified(storage, 60):
            t.writeLog('establish online connection for getting events')
            self.establish()

            events = []
            for cal in calendars:
                cal_items = self.service.events().list(calendarId=cal, timeMin=timeMin, timeMax=timeMax,
                                                        maxResults=maxResult, singleEvents=True,
                                                        orderBy='startTime').execute()
                cal_set = cal_items.get('items', [])

                # set additional attributes

                icon = self.get_calendarBGcolorImage(cal)
                for _record in cal_set:
                    _item = {}
                    _ts = parser.parse(_record['start'].get('dateTime', _record['start'].get('date', '')))
                    _end = parser.parse(_record['end'].get('dateTime', _record['end'].get('date', '')))
                    _tdelta = relativedelta.relativedelta(_end.date(), _ts.date())

                    _item.update({'date': datetime.isoformat(_ts),
                                  'shortdate': _ts.strftime('%d.%m'),
                                  'allday': 0 if _record['start'].get('dateTime') else _tdelta.days,
                                  'timestamp': int(time.mktime(_ts.timetuple())),
                                  'icon': icon,
                                  'id': _record.get('id', ''),
                                  'summary': _record.get('summary', ''),
                                  'description': _record.get('description', None),
                                  'location': _record.get('location', None)})

                    if _record['start'].get('dateTime', False):
                        _item.update({'start': {'dateTime': datetime.isoformat(_ts)}})
                    else:
                        _item.update({'start': {'date': datetime.isoformat(_ts)}})

                    if _record['end'].get('dateTime', False):
                        _item.update({'end': {'dateTime': datetime.isoformat(_end)}})
                    else:
                        _item.update({'end': {'date': datetime.isoformat(_end)}})

                    gadget = _record.get('gadget', None)
                    if gadget:
                        if gadget.get('preferences').get('goo.contactsEventType') == 'BIRTHDAY':
                            _item.update({'specialicon': __cake__})

                    events.append(_item)

            # get additional calendars, glotz.info

            if t.getAddonSetting('glotz_enabled', sType=t.BOOL) and t.getAddonSetting('glotz_apikey') != '':
                if evtype == 'default' or (evtype == 'notification' and t.getAddonSetting('glotz_notify', sType=t.BOOL)):
                    t.writeLog('getting events from glotz.info')
                    try:
                        cal_set = json.loads(urllib.urlopen(self.GLOTZ_URL).read())
                        icon = self.get_calendarBGcolorImage('glotz_color')
                        for _record in cal_set:
                            _item = {}
                            _show = _record.get('show')
                            _time_fmt = 'dateTime'
                            if len(_show.get('airs_time', '')) == 5:
                                _hour = int(_show.get('airs_time')[0:2])
                                _minute = int(_show.get('airs_time')[3:5])
                            else:
                                _hour = 0
                                _minute = 0
                                _time_fmt = 'date'


                            _ts = datetime.fromtimestamp(int(_record.get('first_aired', '0'))).replace(hour=_hour, minute=_minute)
                            _end = _ts + timedelta(minutes=int(_show.get('runtime', '0'))) if _time_fmt == 'dateTime' else _ts

                            _item.update({'timestamp': int(time.mktime(_ts.timetuple())),
                                          'date': datetime.isoformat(_ts),
                                          'shortdate': _ts.strftime('%d.%m'),
                                          'start': {_time_fmt: datetime.isoformat(_ts)},
                                          'end': {_time_fmt: datetime.isoformat(_end)},
                                          'id': '%s-%s-%s' % (_record.get('first_aired', ''), _record.get('season', '0'), _record.get('number', '0')),
                                          'summary': _show.get('network', ''),
                                          'description': '%s - S%02iE%02i: %s' % (_show.get('title', ''),
                                                                                  int(_record.get('season', '0')),
                                                                                  int(_record.get('number', '0')),
                                                                                  _record.get('title', '')),
                                          'icon': icon,
                                          'banner': _show['images'].get('banner', ''),
                                          'allday': 1 if _time_fmt == 'date' else 0})

                            events.append(_item)
                    except Exception as e:
                        t.writeLog('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), level=xbmc.LOGERROR)
                        t.writeLog(type(e).__name__, level=xbmc.LOGERROR)
                        t.writeLog(e.message, level=xbmc.LOGERROR)


            events.sort(key=operator.itemgetter('timestamp'))

            with open(storage, 'w') as filehandle:  json.dump(events, filehandle)
        else:
            t.writeLog('getting events from local storage')
            with open(storage, 'r') as filehandle: events = json.load(filehandle)
        return events

    @classmethod
    def get_event(cls, eventId, storage):
        with open(storage, 'r') as filehandle: events = json.load(filehandle)
        for event in events:
            if event.get('id', '') == eventId: return event
        return False

    @classmethod
    def prepareForAddon(cls, event, timebase=datetime.now(), optTimeStamps=True):

        _ts = parser.parse(event['start'].get('dateTime', event['start'].get('date', '')))
        _end = parser.parse(event['end'].get('dateTime', event['end'].get('date', '')))
        _tdelta = relativedelta.relativedelta(_end.date(), _ts.date())

        if event.get('allday', 0) > 0:
            if _tdelta.months == 0 and _tdelta.weeks == 0 and _tdelta.days == 0: event.update({'range': ''})
            elif _tdelta.months == 0 and _tdelta.weeks == 0 and _tdelta.days == 1: event.update({'range': __LS__(30111)})
            elif _tdelta.months == 0 and _tdelta.weeks == 0: event.update({'range': __LS__(30112) % (_tdelta.days)})
            elif _tdelta.months == 0 and _tdelta.weeks == 1: event.update({'range': __LS__(30113)})
            elif _tdelta.months == 0 and _tdelta.weeks > 0: event.update({'range': __LS__(30114) % (_tdelta.weeks)})
            elif _tdelta.months == 1: event.update({'range': __LS__(30115)})
            elif _tdelta.months > 1: event.update({'range': __LS__(30116) % (_tdelta.months)})
            else: event.update({'range': __LS__(30117)})
        else:
            if _ts != _end:
                event.update({'range': _ts.strftime('%H:%M') + ' - ' + _end.strftime('%H:%M')})
            else:
                event.update({'range': _ts.strftime('%H:%M')})

        if optTimeStamps:
            t.writeLog('calculate additional timestamps')

            _tdelta = relativedelta.relativedelta(_ts.date(), timebase.date())
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
            event.update({'timestamps': ats})

        return event

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
                color = cal.get('backgroundColor', '#808080')
                return t.createImage(15, 40, color, os.path.join(self.COLOR_PATH, color + '.png'))

        color = xbmcgui.Window(10000).getProperty(calendarId)
        if color:
            t.setAddonSetting(calendarId, color)
            xbmcgui.Window(10000).clearProperty(calendarId)
        else:
            color = '#808080'
        return t.createImage(15, 40, color, os.path.join(self.COLOR_PATH, color + '.png'))

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
                event = self.prepareForAddon(event, _now, optTimeStamps=False)
                cur_date = parser.parse(event.get('date'))

                if cur_date.day == dom and cur_date.month == sheet_m and cur_date.year == sheet_y:
                    event_ids += ' %s' % (event['id'])
                    num_events += 1
                    if event.get('allday', 0) > allday: allday = event.get('allday')
                    if event.get('specialicon', '') != '': specialicon = event.get('specialicon')

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
                event = self.prepareForAddon(event, _now, optTimeStamps=self.addtimestamps)
                cur_date = parser.parse(event.get('date'))
                if cur_date.month >= sheet_m and cur_date.year >= sheet_y:
                    if self.addtimestamps:
                        li = xbmcgui.ListItem(label=event['shortdate'] + ' - ' + event['timestamps'], label2=event['summary'],
                                              iconImage=event['icon'])
                    else:
                        li = xbmcgui.ListItem(label=event['shortdate'], label2=event['summary'], iconImage=event['icon'])
                    li.setProperty('id', event.get('id', ''))
                    li.setProperty('range', event.get('range', ''))
                    li.setProperty('allday', str(event.get('allday', 0)))
                    li.setProperty('description', event.get('description') or event.get('location'))
                    li.setProperty('banner', event.get('banner', ''))
                    xbmcplugin.addDirectoryItem(handle, url='', listitem=li)

        xbmcplugin.endOfDirectory(handle, updateListing=True)
