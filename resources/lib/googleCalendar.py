from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

import httplib2
import os
from resources.lib import tinyurl
from resources.lib.simplemail import SMTPMail
import resources.lib.tools as tools

import calendar
import time
import datetime
from dateutil import parser

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
        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())

        # establish service
        self.service = discovery.build('calendar', 'v3', http=http)

        # get colors from google service and store them local
        self.get_colors()

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
            credentials = self.require_credentials(storage)

        return credentials

    def require_credentials(self, storage, require_from_setup=False):
        try:
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, self.SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            flow.user_agent = self.APPLICATION_NAME

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

    def build_sheet(self, events, handle, sheet_y=None, sheet_m=None):
        """
        Building a month calendar sheet and filling days (dom) with events 
        :param events:      event list
        :param sheet_y:     year of the calendar sheet
        :param sheet_m:     month of the calender sheet
        :return:            None
        """
        self.sheet_dom = []
        dom = 1

        # calculate current month/year if not given
        if sheet_m is None: sheet_m = datetime.datetime.today().month
        if sheet_y is None: sheet_y = datetime.datetime.today().year

        _today = None
        if sheet_m == datetime.datetime.today().month and sheet_y == datetime.datetime.today().year:
            _today = datetime.datetime.today().day

        _header = '%s %s' % (__LS__(30119 + sheet_m), sheet_y)
        xbmcgui.Window(10000).setProperty('calendar_header', _header)

        start, sheets = calendar.monthrange(sheet_y, sheet_m)

        for cid in xrange(0, 43):
            if cid < start or cid >= start + sheets:

                # dayly sheets outside of actual month, set these to valid:0
                self.sheet_dom.append({'cid': cid, 'valid': 0})
                continue
            event_list = []
            for event in events:
                _start = event['start'].get('dateTime', event['start'].get('date'))
                dt = parser.parse(_start)

                if dt.day == dom and dt.month == sheet_m and dt.year == sheet_y:
                    event_list.append(event)

            self.sheet_dom.append({'cid': cid, 'valid': 1, 'dom': dom, 'num_events': len(event_list),'events': event_list})
            dom += 1

        if handle is not None:
            for cid in range(0, 43):
                wid = xbmcgui.ListItem(label=str(self.sheet_dom[cid].get('dom')), label2=str(self.sheet_dom[cid].get('num_events')))
                wid.setProperty('valid', str(self.sheet_dom[cid].get('valid')))
                if _today is not None and _today == self.sheet_dom[cid].get('dom'):
                    wid.setProperty('today','1')
                xbmcplugin.addDirectoryItem(handle, url='', listitem=wid)
            xbmcplugin.endOfDirectory(handle, updateListing=True)

