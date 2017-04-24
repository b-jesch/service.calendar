from apiclient import discovery
from oauth2client import client, clientsecrets
from oauth2client.file import Storage

import httplib2
import os
from resources.lib import tinyurl
from resources.lib.simplemail import SMTPMail

import calendar
import datetime
from dateutil import parser

mail = SMTPMail()

# set this properly
# if a property is empty an exception is raised

mail.setproperty(host='')
mail.setproperty(user='')
mail.setproperty(passwd='')
mail.setproperty(sender='')
mail.setproperty(recipient='')

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/service.calendar.json

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CREDENTIALS_DIR = os.path.join(os.getcwd(), '.credentials')
CREDENTIALS_FILE = 'service.calendar.json'
CLIENT_SECRET_FILE = 'service.calendar.auth.json'
APPLICATION_NAME = 'service.calendar'

class Calendar(object):

    class oAuthMissingSecretFile(Exception):
        pass


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
        if not os.path.exists(CREDENTIALS_DIR): os.makedirs(CREDENTIALS_DIR)
        credential_path = os.path.join(CREDENTIALS_DIR, CREDENTIALS_FILE)
        credential_auth = os.path.join(CREDENTIALS_DIR, CLIENT_SECRET_FILE)

        store = Storage(credential_path)
        credentials = store.get()
        if not credentials or credentials.invalid:
            try:
                flow = client.flow_from_clientsecrets(credential_auth, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                flow.user_agent = APPLICATION_NAME

                auth_uri = tinyurl.create_one(flow.step1_get_authorize_url())

                mail.sendmail('\'service.calender\' Anforderung Authentifizierungscode',
                              'Ein Addon fordert einen Code an. Folgen Sie dem Link:\n%s' % (auth_uri))

                print(auth_uri)
                auth_code = raw_input('Enter the authentication code: ')
                credentials = flow.step2_exchange(auth_code)
                store.put(credentials)
            except clientsecrets.InvalidClientSecretsError:
                raise self.oAuthMissingSecretFile()

        return credentials

    def get_colors(self):
        """
        Getting colors from google calender app and store them in property colors
        :return: None
        """
        self.colors = self.service.colors().get().execute()

    def get_color(self, id, scope='calendar'):
        """
        Getting color attributes (foreground, background) for a named color id
        :param id:      color id
        :param scope:   'calendar|item'
        :return:        dict(foreground:#RGB, background: #RGB) or fallback (white, black) 
        """
        return self.colors.get(scope, 'calendar').get(id, {u'foreground': u'#ffffff', u'background': u'#000000'})

    def build_sheet(self, events, sheet_y=None, sheet_m=None):
        """
        Building a month calendar sheet and filling days (dom) with events 
        :param events:      event list
        :param sheet_y:     year of the calendar sheet
        :param sheet_m:     month of the calender sheet
        :return:            None
        """

        # dayly sheet

        self.sheet_dom = []
        dom = 1

        # calculate current month/year if not given
        if sheet_m is None: sheet_m = datetime.datetime.today().month
        if sheet_y is None: sheet_y = datetime.datetime.today().year

        start, sheets = calendar.monthrange(sheet_y, sheet_m)

        for cid in xrange(0,43):
            if cid < start or cid >= start + sheets:

                # dayly sheets outside of actual month, set these to valid:0
                self.sheet_dom.append({'cid': cid, 'valid': 0})
                print sheet_dom[cid]
                continue

            event_list = []
            for event in events:
                _start = event['start'].get('dateTime', event['start'].get('date'))
                dt = parser.parse(_start)

                if dt.day == dom and dt.month == sheet_m and dt.year == sheet_y:
                    event_list.append(event)

            self.sheet_dom.append({'cid': cid, 'valid': 1, 'dom': dom, 'events': event_list})
            print sheet_dom[cid]
            dom += 1
