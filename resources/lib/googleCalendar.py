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

__addonname__ = xbmcaddon.Addon().getAddonInfo('id')
__LS__ = xbmcaddon.Addon().getLocalizedString

mail = SMTPMail()

class Calendar(object):

    class oAuthMissingSecretFile(Exception):
        pass

    class oAuthMissingCredentialsFile(Exception):
        pass

    class MissingStorageFile(Exception):
        pass

    class oAuthIncomplete(Exception):
        pass

    class oAuthFlowExchangeError(Exception):
        pass

    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/service.calendar.json

    if not os.path.exists(os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), '_credentials')):
        os.makedirs(os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), '_credentials'))

    SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
    CLIENT_SECRET_FILE = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')), '_credentials', 'service.calendar.oauth.json')
    CLIENT_CREDENTIALS = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), '_credentials', 'service.calendar.credits.json')
    APPLICATION_NAME = 'service.calendar'

    def __init__(self):
        self.addtimestamps = t.getAddonSetting('additional_timestamps', sType=t.BOOL)

    def establish(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

    def get_credentials(self):
        """
        Gets valid user credentials from storage.

        If nothing has been stored, or if the stored credentials are invalid,
        the OAuth2 flow is completed to obtain the new credentials.

        Returns:
            Credentials, the obtained credential.
        """
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
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
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

    def get_events(self, storage_events, storage_cals, timeMin, timeMax, maxResult=30, calendars='primary'):
        events = []
        for cal in calendars:
            cal_events = self.service.events().list(calendarId=cal, timeMin=timeMin, timeMax=timeMax, maxResults=maxResult,
                                                         singleEvents=True, orderBy='startTime').execute()
            _evs = cal_events.get('items', [])
            if _evs:
                # set additional attributes
                calColor = self.get_calendarBGcolor(cal, storage_cals).replace('#', 'FF').upper()
                for _ev in _evs:
                    _ts = parser.parse(_ev['start'].get('dateTime', _ev['start'].get('date', ''))).timetuple()
                    _ev.update({'timestamp': int(time.mktime(_ts))})
                    _ev.update({'cal_color': calColor})
                events.extend(_evs)

        events.sort(key=operator.itemgetter('timestamp'))
        with open(storage_events, 'w') as filehandle:  json.dump(events, filehandle)

    @classmethod
    def prepare_events(cls, event, timebase=datetime.now(), optTimeStamps=True):

        ev_item = {}

        _dt = parser.parse(event['start'].get('date', event['start'].get('dateTime')))
        ev_item.update({'date': _dt})
        ev_item.update({'shortdate': _dt.strftime('%d.%m')})

        if event['start'].get('date'):
            _allday = '1'
        else:
            _allday = '0'
        if optTimeStamps:
            if _allday == '1':
                _end = parser.parse(event['end'].get('dateTime', event['end'].get('date', '')))
                _tdelta = relativedelta.relativedelta(_end.date(), _dt.date())

                if _tdelta.months == 0 and _tdelta.weeks == 0 and _tdelta.days == 1: ev_item.update({'range': __LS__(30111)})
                elif _tdelta.months == 0 and _tdelta.weeks == 0: ev_item.update({'range': __LS__(30112) % (_tdelta.days)})
                elif _tdelta.months == 0 and _tdelta.weeks == 1: ev_item.update({'range': __LS__(30113)})
                elif _tdelta.months == 0: ev_item.update({'range': __LS__(30114) % (_tdelta.weeks)})
                elif _tdelta.months == 1: ev_item.update({'range': __LS__(30115)})
                else: ev_item.update({'range': __LS__(30116) % (_tdelta.months)})
            else:
                _end = parser.parse(event['end'].get('dateTime', ''))
                if _dt != _end:
                    ev_item.update({'range': _dt.strftime('%H:%M') + ' - ' + _end.strftime('%H:%M')})
                else:
                    ev_item.update({'range': _dt.strftime('%H:%M')})

        ev_item.update({'allday': _allday})
        ev_item.update({'summary': event.get('summary', '')})
        ev_item.update({'description': event.get('description', None)})
        ev_item.update({'location': event.get('location', None)})
        ev_item.update({'cal_color': event.get('cal_color', '#80808080')})

        if optTimeStamps:
            t.writeLog('calculate additional timestamps')
            _tdelta = relativedelta.relativedelta(_dt.date(), timebase.date())

            if _tdelta.months == 0:
                if _tdelta.days == 0: ats = __LS__(30139)
                elif _tdelta.days == 1: ats = __LS__(30140)
                elif _tdelta.days == 2: ats = __LS__(30141)
                elif 3 <= _tdelta.days <= 6: ats = __LS__(30142) % (_tdelta.days)
                elif _tdelta.weeks == 1: ats = __LS__(30143)
                else: ats = __LS__(30144) % (_tdelta.weeks)
            elif _tdelta.months == 1: ats = __LS__(30146)
            else: ats = __LS__(30147) % (_tdelta.months)
            ev_item.update({'timestamps': ats})

        return ev_item

    def set_calendars(self, storage):
        cal_list = self.service.calendarList().list().execute()
        cals = cal_list.get('items', [])
        with open(storage, 'w') as filehandle: json.dump(cals, filehandle)
        return cals

    def get_calendars(self, storage):
        if not os.path.exists(storage):
            raise self.MissingStorageFile('missing %s' % (storage))
        with open(storage, 'r') as filehandle: return json.load(filehandle)

    def get_calendarIdFromSetup(self, setting, storage):
        calId = []
        _cals = t.getAddonSetting(setting).split(', ')
        if len(_cals) == 1 and _cals[0] == 'primary':
            calId.append('primary')
        else:
            cals = self.get_calendars(storage)
            for cal in cals:
                if cal.get('summaryOverride', cal.get('summary', 'primary')) in _cals: calId.append(cal.get('id'))
        t.writeLog('getting cal ids from setup: %s' % (', '.join(calId)))
        return calId

    def get_calendarBGcolor(self, calendarId, storage):
        with open(storage, 'r') as filehandle: cals = json.load(filehandle)
        for cal in cals:
            if cal.get('id') == calendarId: return cal.get('backgroundColor')

    def get_colors(self):
        """
        Getting colors from google calender app and store them in property colors
        :return:            None
        """
        self.colors = self.service.colors().get().execute()

    def get_color(self, color_id, scope='calendar'):
        """
        Getting color attributes (foreground, background) for a named color id
        :param id:          color id
        :param scope:       'calendar|item'
        :return:            dict(foreground:#RGB, background: #RGB) or fallback (white, black)
        """
        return self.colors.get(scope, 'calendar').get(color_id, {u'foreground': u'#ffffff', u'background': u'#000000'})

    def build_sheet(self, handle, storage, content, sheet_y=None, sheet_m=None):
        """
        Building a month calendar sheet and filling days (dom) with events
        :param handle:      plugin handle
        :param storage:     local storage path
        :param content:     calendar content (sheet/event list)
        :param sheet_y:     year of the calendar sheet
        :param sheet_m:     month of the calender sheet
        :return:            None
        """
        self.sheet = []
        dom = 1
        with open(storage, 'r') as filehandle: events = json.load(filehandle)

        # calculate current month/year if not given
        if sheet_m is None: sheet_m = datetime.today().month
        if sheet_y is None: sheet_y = datetime.today().year

        _today = None
        _now = datetime.now()
        if sheet_m == datetime.today().month and sheet_y == datetime.today().year:
            _today = datetime.today().day

        _header = '%s %s' % (__LS__(30119 + sheet_m), sheet_y)
        xbmcgui.Window(10000).setProperty('calendar_header', _header)

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

            event_list = []
            allday = '0'

            for event in events:
                _ev = self.prepare_events(event, _now, optTimeStamps=False)

                if _ev['date'].day == dom and _ev['date'].month == sheet_m and _ev['date'].year == sheet_y:
                    event_list.append(_ev)
                    if _ev['allday'] == '1': allday = '1'

            self.sheet.append({'cid': cid, 'valid': '1', 'dom': str(dom)})
            if len(event_list) > 0: self.sheet[cid].update(num_events=str(len(event_list)), allday=allday, events=event_list)
            if _today == int(self.sheet[cid].get('dom')): self.sheet[cid].update(today='1')
            dom += 1

        if content == 'sheet':
            for cid in range(0, 42):
                cal_sheet = xbmcgui.ListItem(label=self.sheet[cid].get('dom'), label2=self.sheet[cid].get('num_events', '0'))
                cal_sheet.setProperty('valid', self.sheet[cid].get('valid', '0'))
                cal_sheet.setProperty('allday', self.sheet[cid].get('allday', '0'))
                cal_sheet.setProperty('today', self.sheet[cid].get('today', '0'))
                xbmcplugin.addDirectoryItem(handle, url='', listitem=cal_sheet)

        elif content == 'eventlist':
            for event in events:
                _ev = self.prepare_events(event, _now, optTimeStamps=self.addtimestamps)
                if _ev['date'].month >= sheet_m and _ev['date'].year >= sheet_y:
                    if self.addtimestamps:
                        li = xbmcgui.ListItem(label=_ev['shortdate'] + ' - ' + _ev['timestamps'], label2=_ev['summary'])
                    else:
                        li = xbmcgui.ListItem(label=_ev['shortdate'], label2=_ev['summary'])
                    li.setProperty('range', _ev.get('range', ''))
                    li.setProperty('allday', _ev.get('allday', '0'))
                    li.setProperty('cal_color', _ev.get('cal_color'))
                    li.setProperty('description', _ev.get('description') or _ev.get('location') or _ev.get('cal_color'))
                    xbmcplugin.addDirectoryItem(handle, url='', listitem=li)

        xbmcplugin.endOfDirectory(handle, updateListing=True)
