# -*- encoding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import platform
import re
import os
import time

from PIL import Image
from urllib.parse import parse_qsl

ADDON = xbmcaddon.Addon()
ADDONNAME = ADDON.getAddonInfo('id')
PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PROFILES = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
ADDONVERSION = ADDON.getAddonInfo('version')
LS = ADDON.getLocalizedString

# Constants

def STRING():
    return 0

def BOOL():
    return 1

def NUM():
    return 2

def writeLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s %s] %s' % (ADDONNAME, ADDONVERSION, message), level)


TAG_RE = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')


def removeTags(raw):
    if raw is None: return None
    return TAG_RE.sub('', raw)


class Notify(object):
    def __init__(self):
        self.prev_header = ''
        self.prev_message = ''

    def notify(self, header, message, icon=xbmcgui.NOTIFICATION_INFO, dispTime=5000, repeat=False):
        if repeat or (header != self.prev_header or message != self.prev_message):
            xbmcgui.Dialog().notification(header.encode('utf-8'), message, icon, dispTime)
        else:
            writeLog('Message content is same as before, don\'t show notification')
        self.prev_header = header
        self.prev_message = message


class release(object):
    def __init__(self):
        self.platform = platform.system()
        self.hostname = platform.node()
        item = {}
        if self.platform == 'Linux':

            try:
                with open('/etc/os-release', 'r') as _file:
                    for _line in _file:
                        parameter, value = _line.split('=')
                        item[parameter] = value
            except IOError as e:
                writeLog(e.message, xbmc.LOGERROR)

        self.osname = item.get('NAME', 'unknown')
        self.osid = item.get('ID', 'unknown')
        self.osversion = item.get('VERSION_ID', 'unknown')


def lastmodified(path, limit):
    if (int(time.time()) - os.path.getmtime(path)) > limit:
        return False
    else:
        return True


def dialogOK(header, message):
    xbmcgui.Dialog().ok(header.encode('utf-8'), message.encode('utf-8'))


def dialogYesNo(header, message):
    return xbmcgui.Dialog().yesno(header.encode('utf-8'),message.encode('utf-8'))


def dialogKeyboard(header, type=xbmcgui.INPUT_ALPHANUM):
    return xbmcgui.Dialog().input(header.encode('utf-8'), type=type)


def dialogFile(header, type=1):
    _file = xbmcgui.Dialog().browse(type, header, 'files', '', False, False, '', False)
    if _file:
        with open(_file, 'r') as filehandle: return filehandle.read().rstrip()
    return ''


def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    return json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))


def getAddonSetting(setting, sType=STRING, multiplicator=1, isLabel=False):
    try:
        if sType == BOOL:
            return True if ADDON.getSetting(setting).upper() == 'TRUE' else False
        elif sType == NUM:
            try:
                if isLabel:
                    return int(re.match('\d+', LS(int(ADDON.getSetting(setting)))).group()) * multiplicator
                else:
                    return int(re.match('\d+', ADDON.getSetting(setting)).group()) * multiplicator
            except AttributeError:
                return 0
        else:
            return ADDON.getSetting(setting)
    except RuntimeError:
        return None


def setAddonSetting(setting, value):
    ADDON.setSetting(setting, value)


def ParamsToDict(args):
    return dict(parse_qsl(args))


def createImage(width, height, rgbColor, path):
    """
    Creates an RGB image and store it into path
    :param width:       width of image in pixel
    :param height:      height of image in pixel
    :param rgbColor:    color of the background in #RRGGBB hex notation
    :param path:        Path/Name of image
    :return:            True if successful
    """

    if os.path.exists(path): return path
    rgb = rgbColor.lstrip('#')
    # skip transparency
    if len(rgb) == 8: rgb = rgb[2:8]
    lv = len(rgb)
    color = tuple(int(rgb[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    img = Image.new('RGB', (width, height), color)
    img.save(path)
    return path
