# -*- encoding: utf-8 -*-
import smtplib
from email.message import Message
from .tools import *


class SMTPMail(object):
    """
    Send a simple text mail with smtp over
        port 25 (no encryption)
        port 465 (SSL/TLS) or
        port 587 (STARTTLS).
    Only support text, no other MIME or attachments.
    All properties of smtp_client dict must be valid/not empty,
    otherwise an exception is raised.
    """

    class SMTPMailNotDeliveredException(Exception):
        pass

    class SMPTMailParameterException(Exception):
        pass

    smtp_client = dict({
        'host': getAddonSetting('host'),
        'user': getAddonSetting('user'),
        'passwd': getAddonSetting('passwd'),
        'enc': getAddonSetting('enc'),
        'sender': getAddonSetting('sender'),
        'recipient': getAddonSetting('recipient'),
        'charset': getAddonSetting('charset')
    })

    def __init__(self):
        pass

    def setproperty(self, **param):

        if param:
            self.smtp_client.update(param)

    def checkproperties(self):

        for item in self.smtp_client:
            if not self.smtp_client[item] or self.smtp_client[item] == '':
                raise self.SMPTMailParameterException('%s not set' % item)

    def sendmail(self, subject, message):

        try:
            __port = {'None': 25, 'SSL/TLS': 465, 'STARTTLS': 587}
            __enctype = self.smtp_client['enc']
            __msg = Message()
            __msg.set_charset(self.smtp_client['charset'])
            __msg.set_payload(message, charset=self.smtp_client['charset'])
            __msg["From"] = self.smtp_client['sender']
            __msg["To"] = self.smtp_client['recipient']
            __msg["Subject"] = subject

            __conn = smtplib.SMTP(self.smtp_client['host'], __port[__enctype])
            if __enctype == 'STARTTLS' or __enctype == 'SSL/TLS':
                __conn.ehlo()
                if __enctype == 'STARTTLS': __conn.starttls()

            __conn.login(self.smtp_client['user'], self.smtp_client['passwd'])
            __conn.sendmail(self.smtp_client['sender'], self.smtp_client['recipient'], __msg.as_string())
            __conn.close()
        except Exception as e:
            raise self.SMTPMailNotDeliveredException(str(e))
