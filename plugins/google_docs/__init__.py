# -*- coding: UTF-8 -*-
__kupfer_name__ = _("Google Docs")
__kupfer_sources__ = ("GoogleDocsSource", )
__description__ = _("Index files in Google Docs.")
__version__ = "2011-04-03"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import time

import gdata.service
import gdata.docs.service

from kupfer.objects import Source, UrlLeaf
from kupfer.obj.special import PleaseConfigureLeaf, InvalidCredentialsLeaf
from kupfer import plugin_support, pretty

__kupfer_settings__ = plugin_support.PluginSettings(
    dict(
        key='userpass',
        label='',
        type=plugin_support.UserNamePassword,
        value=""))

UPDATE_STARTUP_DELAY = 5  #sec
UPDATE_INTERVAL = 15 * 60  # 15 min


class GoogleDocsLink(UrlLeaf):
    def get_icon_name(self):
        return "document"


def is_plugin_configured():
    upass = __kupfer_settings__['userpass']
    return bool(upass and upass.username and upass.password)


def get_gclient():
    if not is_plugin_configured():
        return None
    gd_client = gdata.docs.service.DocsService(source='kupfer')
    upass = __kupfer_settings__['userpass']
    try:
        gd_client.ClientLogin(upass.username, upass.password)
    except (gdata.service.BadAuthentication,
            gdata.service.CaptchaRequired) as err:
        pretty.print_error(__name__, 'get_gclient', 'authentication error',
                           err)
        upass.password = None
        __kupfer_settings__['userpass'] = upass
        return None
    else:
        return gd_client


def get_docs():
    pretty.print_debug(__name__, 'get_docs start')
    start_time = time.time()

    if not is_plugin_configured():
        yield PleaseConfigureLeaf('google_docs', __kupfer_name__)
        return

    gd_client = get_gclient()
    if gd_client is None:
        yield InvalidCredentialsLeaf('google_docs', __kupfer_name__)
        return

    try:
        for entry in gd_client.GetDocumentListFeed().entry:
            name = entry.title.text.encode('UTF-8')
            link = entry.GetAlternateLink().href
            yield GoogleDocsLink(link, name)
    except gdata.service.Error as err:
        pretty.print_error(__name__, 'get_docs', err)
    pretty.print_debug(__name__, 'get_docs finished',
                       str(time.time() - start_time))


class GoogleDocsSource(Source):
    source_user_reloadable = True

    def __init__(self, name=_("Google Docs")):
        super(GoogleDocsSource, self).__init__(name)

    def initialize(self):
        Source.initialize(self)
        __kupfer_settings__.connect("plugin-setting-changed", self._changed)

    def get_items(self):
        return get_docs() or []

    def provides(self):
        yield UrlLeaf
        yield PleaseConfigureLeaf

    def should_sort_lexically(self):
        return True

    def get_description(self):
        return _("Documents from Google")

    def get_icon_name(self):
        return __name__ + "googledocs"

    def _changed(self, settings, key, value):
        if key == "userpass":
            self.mark_for_update()
