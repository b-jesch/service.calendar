from apiclient import discovery
from oauth2client import client
from oauth2client.file import Storage

import httplib2
import os
from resources.lib import tinyurl
from resources.lib.simplemail import SMTPMail

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
            flow = client.flow_from_clientsecrets(credential_auth, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            flow.user_agent = APPLICATION_NAME
            auth_uri = tinyurl.create_one(flow.step1_get_authorize_url())

            mail.sendmail('\'service.calender\' Anforderung Authentifizierungscode',
                          'Ein Addon fordert einen Code an. Folgen Sie dem Link:\n%s' % (auth_uri))

            print(auth_uri)
            auth_code = raw_input('Enter the authentication code: ')
            credentials = flow.step2_exchange(auth_code)
            store.put(credentials)

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
