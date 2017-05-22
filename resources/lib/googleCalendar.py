from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

import httplib2
import os
from resources.lib import tinyurl
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as tools

import calendar
from datetime import datetime
from dateutil import parser, relativedelta

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
        pass

    def establish(self):
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

        # get colors from google service and store them local
        # self.get_colors()

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

    def require_credentials(self, storage_path, require_from_setup=False, reenter=False):
        storage = Storage(storage_path)
        try:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            flow.user_agent = self.APPLICATION_NAME

            if not reenter:
                auth_uri = tinyurl.create_one(flow.step1_get_authorize_url())

                if require_from_setup:
                    _dialog = __LS__(30082)
                else:
                    _dialog = '%s %s' % (__LS__(30081), __LS__(30082))

                if not tools.dialogYesNo(__LS__(30080), _dialog):
                    raise self.oAuthIncomplete('oAuth2 flow aborted by user')
                tools.dialogOK(__LS__(30080), __LS__(30083))

                mail.checkproperties()
                mail.sendmail(__LS__(30100) % (__addonname__), __LS__(30101) % (auth_uri))

            auth_code = tools.dialogKeyboard(__LS__(30102))
            if auth_code == '':
                raise self.oAuthIncomplete('no key provided')

            credentials = flow.step2_exchange(auth_code)
            storage.put(credentials)
        except client.FlowExchangeError, e:
            raise self.oAuthFlowExchangeError(e.message)

        return credentials

    def get_colors(self):
        """
        Getting colors from google calender app and store them in property colors
        :return:            None
        """
        self.colors = self.service.colors().get().execute()

    def get_color(self, id, scope='calendar'):
        """
        Getting color attributes (foreground, background) for a named color id
        :param id:          color id
        :param scope:       'calendar|item'
        :return:            dict(foreground:#RGB, background: #RGB) or fallback (white, black) 
        """
        return self.colors.get(scope, 'calendar').get(id, {u'foreground': u'#ffffff', u'background': u'#000000'})

    def build_sheet(self, handle, events, content, sheet_y=None, sheet_m=None):
        """
        Building a month calendar sheet and filling days (dom) with events 
        :param events:      event list
        :param sheet_y:     year of the calendar sheet
        :param sheet_m:     month of the calender sheet
        :return:            None
        """
        self.sheet = []
        dom = 1

        # calculate current month/year if not given
        if sheet_m is None: sheet_m = datetime.today().month
        if sheet_y is None: sheet_y = datetime.today().year

        _today = None
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
                _start = event['start'].get('date', event['start'].get('dateTime'))
                dt = parser.parse(_start)

                if dt.day == dom and dt.month == sheet_m and dt.year == sheet_y:
                    event_list.append(event)
                    if event['start'].get('date'): allday = '1'

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
            _now = datetime.now()
            for event in events:
                _start = event['start'].get('date', event['start'].get('dateTime'))
                _dt = parser.parse(_start)
                _daydiff = relativedelta.relativedelta(_dt.date(), _now.date()).days

                # calculate acronyms
                if _daydiff == 1:
                    acr = __LS__(30140)
                elif _daydiff == 2:
                    acr = __LS__(30141)
                elif 3 <= _daydiff <= 6:
                    acr = __LS__(30142) % (_daydiff)
                elif _daydiff / 7 == 1:
                    acr = __LS__(30143)
                else:
                    acr = __LS__(30144) % (_daydiff / 7)

                if _dt.month >= sheet_m and _dt.year >= sheet_y:
                    li = xbmcgui.ListItem(label=_dt.strftime('%d.%m') + ' - ' + acr, label2=event['summary'])
                    # li = xbmcgui.ListItem(label=acr, label2=event['summary'])
                    if event['start'].get('date'):
                        li.setProperty('range', __LS__(30111))
                        li.setProperty('allday','1')
                    else:
                        dtstart = parser.parse(event['start'].get('dateTime', ''))
                        dtend = parser.parse(event['end'].get('dateTime', ''))
                        if dtstart != dtend:
                            li.setProperty('range', dtstart.strftime('%H:%M') + ' - ' + dtend.strftime('%H:%M'))
                        else:
                            li.setProperty('range', dtstart.strftime('%H:%M'))
                    try:
                        li.setProperty('description', event['description'])
                    except KeyError:
                        pass

                    xbmcplugin.addDirectoryItem(handle, url='', listitem=li)

        xbmcplugin.endOfDirectory(handle, updateListing=True)
