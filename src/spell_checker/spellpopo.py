# -*- coding: utf-8 -*-
# Copyright: (C) 2019-2021 Lovac42
# Support: https://github.com/lovac42/SpellingPolice
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


# TODO:
#   Auto download dicts from github


from aqt.qt import *
from aqt import mw
from aqt.webview import AnkiWebView
from anki.hooks import wrap, addHook
from anki.lang import _
from functools import partial
from pathlib import Path
import shutil

from .dict import DictionaryManager
from .config import Config
from .const import BUNDLED_DICTS_DIR, DICT_DIR

ADDON_NAME = "Spell Checker with Custom Dictionaries"
conf = Config(ADDON_NAME)

dictMan = DictionaryManager()


def replaceMisspelledWord(page, sug_word):
    page.replaceMisspelledWord(sug_word)


def onContextMenuEvent(web: AnkiWebView, menu):
    profile = web._page.profile()

    # For Edit field during review
    if mw.state == "review":
        if not conf.get("check_during_review", False):
            return
        profile.setSpellCheckLanguages(dictMan.getDictionaries())

    spellCheckEnabled = profile.isSpellCheckEnabled()
    print(f"{spellCheckEnabled=}")
    menu.addSeparator()
    action = menu.addAction(_("Spell Checker"))
    action.setCheckable(True)
    action.setChecked(spellCheckEnabled)
    action.triggered.connect(
        lambda: profile.setSpellCheckEnabled(not spellCheckEnabled)
    )

    if spellCheckEnabled and conf.get("duck_mode", False):
        firstAct = menu.actions()[0]
        data = _contextMenuRequest(web)
        for sug_word in data.spellCheckerSuggestions():
            action = menu.addAction(sug_word)
            menu.insertAction(firstAct, action)
            action.triggered.connect(
                partial(replaceMisspelledWord, web._page, sug_word)
            )
            if conf.get("bold_text", True):
                f = action.font()
                f.setBold(True)
                action.setFont(f)
        menu.insertSeparator(firstAct)


def _contextMenuRequest(web: AnkiWebView):
    if qtmajor == 5:
        return web.page().contextMenuData()
    elif qtmajor == 6:
        return web.lastContextMenuRequest()
    else:
        raise RuntimeError("unkown qt version")


def install_initial_dictionaries():
    installed_dict = conf.get("installed_dict", {})
    for child in Path(BUNDLED_DICTS_DIR).iterdir():
        if child.is_file() and child.suffix == ".bdic":
            name = child.stem
            if not installed_dict.get(name, False):
                shutil.copy(child, DICT_DIR)
            installed_dict[name] = True
            # Save progress even if one dict fails to install
            conf.set("installed_dict", installed_dict)


install_initial_dictionaries()

addHook("EditorWebView.contextMenuEvent", onContextMenuEvent)
addHook("AnkiWebView.contextMenuEvent", onContextMenuEvent)


def setupBDIC(web: AnkiWebView, *args, **kwargs):
    profile = web._page.profile()
    profile.setSpellCheckEnabled(conf.get("auto_startup", False))
    profile.setSpellCheckLanguages(dictMan.getDictionaries())


AnkiWebView.__init__ = wrap(AnkiWebView.__init__, setupBDIC, "after")
