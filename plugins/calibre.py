# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Calibre")
__kupfer_sources__ = ("LibrariesSource", )
__description__ = _("Book in Calibre Library")
__version__ = "2013-08-08"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"

'''
Changes:
	2013-08-08: init
'''

import os
from xml.etree import cElementTree as ElementTree
import sqlite3
from contextlib import closing

from kupfer.objects import Source, FileLeaf, Leaf, SourceLeaf
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.fileactions import Open

_HISTORY_FILE = '~/.config/calibre/history.plist'
_METADATA_FILE = 'metadata.db'
_CALIBRE_GLOBAL = '~/.config/calibre/global.py'


def plist_to_dict(nodes):
	key = None
	for node in nodes:
		if node.tag == 'key':
			key = node.text
		elif node.tag == 'array':
			if key:
				yield key, [cnode.text for cnode in node.getchildren()]
				key = None


def get_default_library_path():
	global_path = os.path.expanduser(_CALIBRE_GLOBAL)
	if not os.path.isfile(global_path):
		return None
	with open(global_path, 'r') as global_file:
		for row in global_file:
			if not row.startswith('library_path = '):
				continue
			try:
				library_path = str(eval(row[15:]))
				return library_path if os.path.isdir(library_path) else None
			except:
				pass
	return None


class BooksSource(Source):
	def __init__(self, library_path):
		Source.__init__(self, os.path.basename(library_path))
		self.library_path = library_path

	def get_description(self):
		return "Calibre Library %s" % self.name

	def repr_key(self):
		return self.library_path

	def get_items(self):
		metadata_file = os.path.join(self.library_path, _METADATA_FILE)
		if not os.path.isfile(metadata_file):
			return
		with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
			curs = conn.cursor()
			curs.execute("select b.id, sort, author_sort, path, name, format "
					"from books b left join data d "
					"on b.id = d.book "
					"order by sort, format")
			for book_id, title, author, path, name, format_ in curs:
				default_book = name + "." + format_.lower()
				yield BookLeaf(default_book, book_id, title, author,
						os.path.join(self.library_path, path), metadata_file)

	def provides(self):
		yield BookLeaf


class BookLeaf(Leaf):
	def __init__(self, default_book, book_id, title, author, path, metadata_file):
		Leaf.__init__(self, os.path.join(path, default_book), title)
		self.book_id = book_id
		self.author = author
		self.path = path
		self.metadata_file = metadata_file
		self.kupfer_add_alias(path)

	def get_description(self):
		return self.author

	def has_content(self):
		return True

	def content_source(self, alternate=False):
		return BookContentSource(self.book_id, self.name, self.path,
				self.metadata_file)

	def get_actions(self):
		yield Open()


class LibrariesSource (AppLeafContentMixin, Source, FilesystemWatchMixin):
	appleaf_content_id = 'calibre-gui'

	def __init__(self, name=_("Calibre Libraries")):
		Source.__init__(self, name)

	def initialize(self):
		hist_file_path = os.path.expanduser(_HISTORY_FILE)
		if os.path.exists(hist_file_path):
			calibre_config_dir = os.path.dirname(hist_file_path)
			self.monitor_token = self.monitor_directories(calibre_config_dir)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() in ('history.plist', 'global.py')

	def get_items(self):
		default_library = get_default_library_path()
		if default_library:
			yield SourceLeaf(BooksSource(default_library))
		hist_file_path = os.path.expanduser(_HISTORY_FILE)
		if not os.path.exists(hist_file_path):
			return
		self.output_debug('reading', hist_file_path)
		try:
			tree = ElementTree.parse(hist_file_path)
			history = dict(plist_to_dict(tree.find('dict')))
			if not 'lineedit_history_choose_library_dialog' in history:
				return
			for item in history['lineedit_history_choose_library_dialog']:
				yield SourceLeaf(BooksSource(item))
		except StandardError, err:
			self.output_error(err)

	def get_description(self):
		return _("Calibre Libraries")

	def provides(self):
		yield SourceLeaf


class BookContentSource(Source):
	def __init__(self, book_id, title, path, metadata_file):
		Source.__init__(self, title)
		self.path = path
		self.book_id = book_id
		self.metadata_file = metadata_file

	def get_items(self):
		with closing(sqlite3.connect(self.metadata_file, timeout=1)) as conn:
			curs = conn.cursor()
			curs.execute("select format, name from data "
					"where book=? "
					"order by format", (self.book_id, ))
			for format_, name in curs:
				yield FileLeaf(os.path.join(self.path, name + "." +
						format_.lower()))

	def repr_key(self):
		return (self.book_id, self.path)

	def get_description(self):
		return _("Calibre Book")

	def provides(self):
		yield FileLeaf
