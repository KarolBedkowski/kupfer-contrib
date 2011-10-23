# -*- coding: UTF-8 -*-
'''
Lookup TextLeaf in StarDict dictionares.

Require: pyStarDict https://github.com/lig/pystardict

'''
__kupfer_name__ = _("StarDict")
__kupfer_actions__ = ("Lookup", )
__description__ = _("Lookup text with StarDict.\nPlugin require installed "
		"dictionaries in StarDict format.")
__version__ = "2011-07-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

import os
import re

from kupfer.objects import Source, Action, TextLeaf, Leaf
from kupfer import icons
from kupfer import plugin_support

import pystardict

__kupfer_settings__ = plugin_support.PluginSettings(
	{
		'key': 'dictdirs',
		'label': _("Dictionaries location (;-separated):"),
		'type': str,
		'value': "/usr/share/stardict/dic/",
	},
)


class Lookup (Action):
	def __init__(self):
		Action.__init__(self, _("Lookup In..."))

	def activate(self, leaf, iobj):
		text = unicode(leaf.object)
		return _LookupSource(text, iobj)

	def is_factory(self):
		return True

	def item_types(self):
		yield TextLeaf

	def valid_for_item(self, leaf):
		return len(leaf.object.strip()) > 0

	def get_description(self):
		return _("Lookup text in StarDict dictionary")

	def get_icon_name(self):
		return "accessories-dictionary"

	def requires_object(self):
		return True

	def object_types(self):
		yield Dictionary

	def object_source(self, for_item=None):
		return DictSource()


class _LookupSource(Source):
	def __init__(self, text, dictionary):
		Source.__init__(self, name=_("Lookup into %s") % unicode(Dictionary))
		self._text = text
		self._dict = dictionary

	def repr_key(self):
		return (hash(self._text), self._dict)

	def get_items(self):
		for translation in _lookup(self._dict.object, self._text):
			translation = translation.strip()
			if translation:
				yield TranslationLeaf(translation,
						_("%s in %s") % (self._text, unicode(self._dict)))


class Dictionary(Leaf):
	serializable = 1

	def get_gicon(self):
		return icons.ComposedIcon("text-x-generic", "preferences-desktop-locale")


class TranslationLeaf(TextLeaf):
	def __init__(self, translation, descr):
		TextLeaf.__init__(self, translation)
		self._descrtiption = descr

	def get_description(self):
		return self._descrtiption or TextLeaf.get_description(self)


# cache for Languages (load it once)
_DICT_CACHE = None


class DictSource(Source):

	def __init__(self):
		Source.__init__(self, _("Languages"))

	def get_items(self):
		global _DICT_CACHE
		if not _DICT_CACHE:
			_DICT_CACHE = tuple((Dictionary(name, key)
					for key, name in _load_dictionares()))
		return _DICT_CACHE

	def provides(self):
		yield Dictionary

	def get_icon_name(self):
		return "preferences-desktop-locale"


def _load_dictionares():
	dirs = __kupfer_settings__['dictdirs']
	if not dirs:
		return
	for dictdir in dirs.split(';'):
		print dictdir
		if not os.path.isdir(dictdir):
			continue
		for filename in os.listdir(dictdir):
			if not filename.endswith('.ifo'):
				continue
			ifopath = os.path.join(dictdir, filename)
			try:
				with open(ifopath, 'rt') as ifo:
					for line in ifo:
						if line.startswith('bookname'):
							name = line.split('=')[1].strip()
							yield name, ifopath[:-4]
			except:
				pass


_RE_CLEAN = re.compile(r'<\/?.+?>')


def _lookup(dictionary, word):
	sdict = pystardict.Dictionary(dictionary)
	if word in sdict:
		data = sdict[word].replace('<br>', '\n').replace('\0', '\n')
		data = re.sub(_RE_CLEAN, '', data)
		return data.split('\n')
	return []
