# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Deep Directories")
__kupfer_sources__ = ("DeepDirSource", )
__description__ = _("Recursive index directories")
__version__ = "2012-06-08"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Changes:
	2012-06-08 - init
'''

import os

from kupfer.obj import sources
from kupfer import plugin_support


__kupfer_settings__ = plugin_support.PluginSettings(
	{
		'key': 'dirs',
		'label': _("Directories (;-separated):"),
		'type': str,
		'value': "~/Documents/",
	},
	{
		'key': 'depth',
		'label': _("Depth"),
		'type': int,
		'value': 5,
	},
)


class DeepDirSource(sources.FileSource):
	def __init__(self, name=_("Deep Directories")):
		sources.FileSource.__init__(self, self._get_dirs(),
				__kupfer_settings__['depth'])

	def initialized(self):
		__kupfer_settings__.connect("plugin-setting-changed",
				self._setting_changed)

	def get_items(self):
		self.dirlist = self._get_dirs()
		self.depth = __kupfer_settings__['depth']
		return sources.FileSource.get_items(self)

	def _get_dirs(self):
		if not __kupfer_settings__['dirs']:
			return []
		res = [os.path.expanduser(path) for path
				in __kupfer_settings__['dirs'].split(';')]
		return filter(os.path.isdir, res)

	def _setting_changed(self, settings, key, value):
		if key in ('dirs', 'depth'):
			self.mark_for_update()
