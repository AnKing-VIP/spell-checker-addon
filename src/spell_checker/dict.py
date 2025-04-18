# -*- coding: utf-8 -*-
# Copyright: (C) 2019-2021 Lovac42
# Support: https://github.com/lovac42/SpellingPolice
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


import os
import re
from typing import Optional, Union, List

from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, showInfo, tooltip

from .const import *
from .bdicwriter import create_bdic
from .anking_menu import get_anking_menu
from .get_dicts import invokeGetDicts


def open_dict_dir() -> None:
    if os.path.exists(DICT_DIR):
        openFolder(DICT_DIR)
    elif ALT_BUILD_VERSION:
        from aqt import moduleDir

        openFolder(moduleDir)

    if ALT_BUILD_VERSION:
        showInfo(ALT_BUILD_INSTRUCTIONS, title="Instructions", textFormat="rich")

def verbose_name(filename: str) -> str:
    """Get verbose dictionary name from filename"""
    langcode_re = re.compile(r"^([a-z]{2}-[A-Z]{2}|[a-z]{2})-")
    matches = langcode_re.findall(filename)
    if not matches:
        return filename
    vn = langs.get(matches[0], None)
    if vn is None:
        # try ISO 639-1 language code without ISO 3166-1 country code
        iso639 = matches[0].split("-")[0]
        vn = langs.get(iso639, None)
    if vn is None:
        return filename
    return vn  + " - " + filename

def build_custom_dictionary(parent: QWidget, words: List[str]) -> bool:
    words = list(sorted(set(words)))
    # Delete dictionary if no words exist
    if len(words) == 0:
        Path(CUSTOM_DICT_FILE).unlink(missing_ok=True)
        Path(CUSTOM_WORDS_TEXT_FILE).write_text("")
        return True
    # Custom dictionary must have at least 2 words or an error occurs
    if len(words) == 1:
        additional = "a" if "a" not in words else "I"
        words.append(additional)
        tooltip(
            f"Additionally added word '{additional}' because a dictionary must contain at least 2 words.",
            period=6000,
            parent=parent,
        )

    aff: Optional[str] = None
    aff_file = Path(CUSTOM_WORDS_AFF_FILE)
    if aff_file.exists():
        aff = aff_file.read_text()
    else:
        invalid_char = filter(lambda word: "/" in word, words)
        if next(invalid_char, None) != None:
            showInfo("One of the words contain invalid character '/'. Aborting.", parent=parent)
            return False
    content = create_bdic(words, aff)
    Path(CUSTOM_DICT_FILE).write_bytes(content)
    Path(CUSTOM_WORDS_TEXT_FILE).write_text("\n".join(words))

    return True

def add_word_to_custom_dictionary(parent: QWidget, word: str) -> None:
    Path(CUSTOM_WORDS_TEXT_FILE).touch(exist_ok=True)
    words = Path(CUSTOM_WORDS_TEXT_FILE).read_text().splitlines()
    words.append(word)
    build_custom_dictionary(parent, words)


class DictionaryManager:
    def __init__(self):
        self.setupMenu()

        self._dicts = [
            i[:-5] for i in os.listdir(DICT_DIR) if RE_DICT_EXT_ENABLED.search(i)
        ]

    def setupMenu(self):
        menu = get_anking_menu()
        a = QAction("Spell Checker Dictionaries", menu)
        menu.addAction(a)
        a.triggered.connect(self.showConfig)

    def showConfig(self):
        profile = mw.web.page().profile()

        profile.setSpellCheckEnabled(False)
        profile.setSpellCheckLanguages({})
        self._dicts = DictionaryDialog().getDictionaries()

        profile.setSpellCheckEnabled(profile.isSpellCheckEnabled())
        profile.setSpellCheckLanguages(self._dicts)

    def getDictionaries(self):
        return self._dicts


class DictionaryDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self._setupDialog()
        self._update()
        self.exec()

    def getDictionaries(self):
        return self._dict

    def _setupDialog(self):
        self.setWindowTitle("Dictionaries")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(250, 250)

        layout = QVBoxLayout()
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self._toggle)

        bws_btn = QPushButton("Browse")
        bws_btn.clicked.connect(open_dict_dir)
        custom_words_btn = QPushButton("Custom Dictionary")
        custom_words_btn.clicked.connect(lambda _: CustomDicDialog(parent=self).exec())
        en_btn = QPushButton("Enable")
        en_btn.clicked.connect(self._enable)
        dis_btn = QPushButton("Disable")
        dis_btn.clicked.connect(self._disable)
        download_btn = QPushButton("Download")
        download_btn.clicked.connect(self._download)

        control_box = QHBoxLayout()
        control_box.addWidget(bws_btn)
        control_box.addWidget(download_btn)
        control_box.addWidget(custom_words_btn)
        control_box.addStretch(0)
        control_box.addWidget(en_btn)
        control_box.addWidget(dis_btn)

        layout.addWidget(self.list)
        layout.addLayout(control_box)
        self.setLayout(layout)

    def _download(self):
        invokeGetDicts(parent=self)
        self._update()

    def _update(self):
        self._dict = []
        self.list.clear()

        try:
            DICT_FILES = os.listdir(DICT_DIR)
        except FileNotFoundError:
            showInfo("Missing or no read/write permission to dictionary folder.")
            return

        for d in DICT_FILES:
            if RE_DICT_EXT_ENABLED.search(d):
                item = QListWidgetItem(verbose_name(d))
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.list.addItem(item)
                self._dict.append(d[:-5])

        for d in DICT_FILES:
            if RE_DICT_EXT_DISABLED.search(d):
                item = QListWidgetItem(verbose_name(d))
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.list.addItem(item)

    def _enable(self):
        sel = [i for i in range(self.list.count()) if self.list.item(i).isSelected()]
        if sel:
            for i in sel:
                fn = self.list.item(i).data(Qt.ItemDataRole.UserRole)
                if RE_DICT_EXT_DISABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f[:-9])
        self._update()

    def _disable(self):
        sel = [i for i in range(self.list.count()) if self.list.item(i).isSelected()]
        if sel:
            for i in sel:
                fn = self.list.item(i).data(Qt.ItemDataRole.UserRole)
                if RE_DICT_EXT_ENABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f + ".disabled")
        self._update()

    def _toggle(self):
        fn = self.list.currentItem().text()
        if RE_DICT_EXT_ENABLED.search(fn):
            self._disable()
        else:
            self._enable()


class CustomDicDialog(QDialog):
    saved = False
    parent: QDialog

    def __init__(self, parent: QDialog):
        QDialog.__init__(self, parent)
        self.parent = parent
        Path(CUSTOM_WORDS_TEXT_FILE).touch(exist_ok=True)
        self._setup_dialog()
        self.load_words()

    def _setup_dialog(self) -> None:
        self.setWindowTitle("Custom Dictionary")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(600, 300)

        instruction_text = QLabel("Put one word in each line. Restart Anki afterwards.")
        instruction_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        text_edit = QTextEdit(self)
        text_edit.setAcceptRichText(False)
        text_edit.setMaximumHeight(9999)
        self.text_edit = text_edit

        button_box = QDialogButtonBox(self)
        button_box.setOrientation(Qt.Orientation.Horizontal)
        button_box.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addSpacing(3)
        layout.addWidget(instruction_text)
        layout.addWidget(text_edit)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_words(self) -> None:
        text = Path(CUSTOM_WORDS_TEXT_FILE).read_text()
        self.text_edit.setPlainText(text)

    def accept(self) -> None:
        words = self.text_edit.toPlainText().splitlines()
        if build_custom_dictionary(self, words):
            self.saved = True
            QDialog.accept(self)

    def reject(self) -> None:
        if not self.saved:
            resp = QMessageBox.question(
                self,
                "Discard changes?",
                "Closing this window will discard changes. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
        QDialog.reject(self)
