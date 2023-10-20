# -*- coding: utf-8 -*-
# Copyright: (C) 2018-2020 Lovac42
# Support: https://github.com/lovac42/AddonManager21
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Version: 0.0.6


import os
import re
from codecs import open
from typing import Mapping

from anki import version
from anki.hooks import addHook, runHook
from anki.utils import json
from aqt import mw
from aqt.qt import *

version_re = re.compile(r"^(?P<year>\d*)\.(?P<month>\d*)(\.(?P<patch>\d*))?$")
mo = version_re.search(version)
ANKI21 = version.startswith("2.1.") or int(mo.group("year")) >= 23


class Config:
    config = {}

    def __init__(self, addonName):
        self.addonName = addonName
        self._loadConfig()

    def set(self, key, value):
        self.config[key] = value
        self._saveConfig()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def has(self, key):
        return self.config.get(key) != None

    def _loadConfig(self):
        if getattr(mw.addonManager, "getConfig", None):
            mw.addonManager.setConfigUpdatedAction(__name__, self._updateConfig)
            # self.config=mw.addonManager.getConfig(__name__)
        # else:
        self.config = self._readConfig()
        runHook(self.addonName + ".configLoaded")  # don't know what this is here for?

    def _updateConfig(self, config):
        self.config = nestedUpdate(self.config, config)
        runHook(self.addonName + ".configUpdated")  # don't know what this is here for?

    def _readConfig(self):
        conf = self.readFile("config.json")
        meta = self.readFile("meta.json")
        if meta:
            conf = nestedUpdate(conf, meta.get("config", {}))
        return conf

    def readFile(self, fname, jsn=True):
        moduleDir, _ = os.path.split(__file__)
        path = os.path.join(moduleDir, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
            if jsn:
                return json.loads(data)
            return data

    def _saveConfig(self):
        mw.addonManager.writeConfig(__name__, self.config)


# From: https://stackoverflow.com/questions/3232943/
def nestedUpdate(d, u):
    if ANKI21:  # py3.3+
        itms = u.items()
    else:  # py2.7
        itms = u.iteritems()
    for k, v in itms:
        if isinstance(v, Mapping):
            d[k] = nestedUpdate(d.get(k, {}), v)
        else:
            d[k] = v
    return d
