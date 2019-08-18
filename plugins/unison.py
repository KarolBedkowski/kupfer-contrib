# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Unison")
__kupfer_sources__ = ("UnisonProfilesSource", )
__kupfer_actions__ = ("OpenProfile", )
__description__ = _("Union profiles")
__version__ = "2019-08-18"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os

from kupfer import utils
from kupfer.objects import Source, Leaf, Action
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.apps import AppLeafContentMixin

_UNISON_DIR = '~/.unison/'


class ProfileLeaf(Leaf):
    def __init__(self, name):
        Leaf.__init__(self, name, name[:-4])

    def get_actions(self):
        yield OpenProfile()

    def get_icon_name(self):
        return 'unison-gtk'


class UnisonProfilesSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
    appleaf_content_id = 'unison-gtk'

    def __init__(self, name=_("Unison Profiles")):
        Source.__init__(self, name)

    def initialize(self):
        self.monitor_token = self.monitor_directories(
            os.path.expanduser(_UNISON_DIR))

    def get_items(self):
        unison_path = os.path.expanduser(_UNISON_DIR)
        if not os.path.isdir(unison_path):
            return
        for filename in os.listdir(unison_path):
            if filename.endswith('.prf'):
                yield ProfileLeaf(filename)

    def get_icon_name(self):
        return 'unison-gtk'

    def provides(self):
        yield ProfileLeaf


class OpenProfile(Action):
    """ Open Calibre Library"""

    def __init__(self):
        Action.__init__(self, _("Open in Unison"))

    def activate(self, leaf):
        utils.spawn_async(
            ["unison",  str(leaf.object)])

    def get_icon_name(self):
        return 'document-open'
