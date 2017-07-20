# -*- encoding: utf-8 -*-

import os
import xbmc
import xbmcgui

import tools

ACTION_SELECT = 7
ACTION_SHOW_INFO = 11
ACTION_NAV_BACK = 92

BaseWindow = xbmcgui.WindowXMLDialog

class DialogKaiToast(BaseWindow):

    AVATAR_ID = 400
    LABEL_1_ID = 401
    LABEL_2_ID = 402

    def __init__(self, *args, **kwargs):

        self.label_1 = None
        self.label_2 = None
        self.icon = None

    @staticmethod
    def createDialogKaiToast():
        return DialogKaiToast('DialogNotification.xml', os.getcwd())

    def onAction(self, action):

        tools.writeLog('Action received: ID %s' % str(action.getId()))
        if (action == ACTION_NAV_BACK) or (action == ACTION_SELECT) or (action == ACTION_SHOW_INFO):
            xbmcgui.Window(10000).setProperty('reminders', '0')
            tools.writeLog('Display of notifications aborted by user', level=xbmc.LOGNOTICE)
            self.close()

    def onInit(self):
        tools.writeLog('Init notification window')
        self.getControl(DialogKaiToast.AVATAR_ID).setImage(self.icon)
        try:
            if hasattr(self.getControl(DialogKaiToast.LABEL_1_ID), 'addLabel'):
                self.getControl(DialogKaiToast.LABEL_1_ID).addLabel(self.label_1)
            elif hasattr(self.getControl(DialogKaiToast.LABEL_1_ID), 'setText'):
                self.getControl(DialogKaiToast.LABEL_1_ID).setText(self.label_1)
            else:
                pass
            if hasattr(self.getControl(DialogKaiToast.LABEL_2_ID), 'addLabel'):
                self.getControl(DialogKaiToast.LABEL_2_ID).addLabel(self.label_2)
            elif hasattr(self.getControl(DialogKaiToast.LABEL_2_ID), 'setText'):
                self.getControl(DialogKaiToast.LABEL_2_ID).setText(self.label_2)
            else:
                pass
        except AttributeError, e:
            tools.writeLog('could not set all attributes to DialogKaiToast properly', xbmc.LOGFATAL)
            tools.writeLog(e.message, xbmc.LOGFATAL)

    @classmethod
    def onClick(cls, controlID):
        tools.writeLog('click received: ID %s' % (controlID))

    def close(self):
        BaseWindow.close(self)
        tools.writeLog('Close notification window')
