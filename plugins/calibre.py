# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Calibre")
__kupfer_sources__ = ("LibrariesSource", "AllBooksSource", "AuthorsSource",
		"SeriesSource")
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


def get_libraries():
	default_library = get_default_library_path()
	if default_library:
		yield default_library

	hist_file_path = os.path.expanduser(_HISTORY_FILE)
	if not os.path.exists(hist_file_path):
		return
	print 'reading', hist_file_path
	try:
		tree = ElementTree.parse(hist_file_path)
		history = dict(plist_to_dict(tree.find('dict')))
		if not 'lineedit_history_choose_library_dialog' in history:
			return
		for item in history['lineedit_history_choose_library_dialog']:
			yield item
	except StandardError, err:
		print err


def get_books_from_library(library_path):
	metadata_file = os.path.join(library_path, _METADATA_FILE)
	if not os.path.isfile(metadata_file):
		return
	with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
		curs = conn.cursor()
		curs.execute("select b.id, sort, author_sort, path, "
			"    (select name || '.' || lower(format) from data d "
			"       where book=b.id limit 1) as format "
			"from books b "
			"order by sort, format")
		for book_id, title, author, path, default_book in curs:
			yield BookLeaf(default_book, book_id, title, author,
					os.path.join(library_path, path), metadata_file)


def get_books_from_library_by_author(library_path, author_id):
	metadata_file = os.path.join(library_path, _METADATA_FILE)
	if not os.path.isfile(metadata_file):
		return
	with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
		curs = conn.cursor()
		curs.execute("select b.id, sort, author_sort, path, "
			"    (select name || '.' || lower(format) from data d "
			"       where book=b.id limit 1) as format "
			"from books_authors_link a join books b "
			"on a.book = b.id "
			"where a.author=? "
			"order by sort, format", (author_id, ))
		for book_id, title, author, path, default_book in curs:
			yield BookLeaf(default_book, book_id, title, author,
					os.path.join(library_path, path), metadata_file)


def get_books_from_library_by_series(library_path, series_id):
	metadata_file = os.path.join(library_path, _METADATA_FILE)
	if not os.path.isfile(metadata_file):
		return
	with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
		curs = conn.cursor()
		curs.execute("select b.id, sort, author_sort, path, "
			"    (select name || '.' || lower(format) from data d "
			"       where book=b.id limit 1) as format "
			"from books_series_link a join books b "
			"on a.book = b.id "
			"where a.series=? "
			"order by sort, format", (series_id, ))
		for book_id, title, author, path, default_book in curs:
			yield BookLeaf(default_book, book_id, title, author,
					os.path.join(library_path, path), metadata_file)


def get_authors_from_library(library_path):
	metadata_file = os.path.join(library_path, _METADATA_FILE)
	if not os.path.isfile(metadata_file):
		return
	with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
		curs = conn.cursor()
		curs.execute("select id, name, sort from authors order by sort")
		for author_id, name, name_sort in curs:
			yield AuthorLeaf(author_id, name, name_sort, library_path)


def get_series_from_library(library_path):
	metadata_file = os.path.join(library_path, _METADATA_FILE)
	if not os.path.isfile(metadata_file):
		return
	with closing(sqlite3.connect(metadata_file, timeout=1)) as conn:
		curs = conn.cursor()
		curs.execute("select id, name, sort from series order by sort")
		for series_id, name, name_sort in curs:
			yield SeriesLeaf(series_id, name, name_sort, library_path)


def _get_dirs_to_monitor():
	dirs = []
	hist_file_path = os.path.expanduser(_HISTORY_FILE)
	if os.path.exists(hist_file_path):
		dirs.append(os.path.dirname(hist_file_path))
	dirs.extend(get_libraries())
	return dirs


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


class AuthorLeaf(Leaf):
	def __init__(self, author_id, name, name_sort, library_path):
		Leaf.__init__(self, author_id, name_sort)
		self.kupfer_add_alias(name)
		self.library_path = library_path

	def has_content(self):
		return True

	def content_source(self, alternate=False):
		return AuthorContentSource(self.object, self.name, self.library_path)


class SeriesLeaf(Leaf):
	def __init__(self, series_id, name, name_sort, library_path):
		Leaf.__init__(self, series_id, name_sort)
		self.kupfer_add_alias(name)
		self.library_path = library_path

	def has_content(self):
		return True

	def content_source(self, alternate=False):
		return SeriesContentSource(self.object, self.name, self.library_path)


class LibraryBooksSource(Source):
	def __init__(self, library_path):
		Source.__init__(self, os.path.basename(library_path))
		self.library_path = library_path

	def get_description(self):
		return "Calibre Library %s" % self.name

	def repr_key(self):
		return self.library_path

	def get_items(self):
		yield SourceLeaf(AuthorsSource(self.library_path,
				name=_("<Calibre Authors>")))
		yield SourceLeaf(SeriesSource(self.library_path,
				name=_("<Calibre Series>")))
		for book in get_books_from_library(self.library_path):
			yield book

	def provides(self):
		yield BookLeaf
		yield AuthorLeaf


class AuthorContentSource(Source):
	def __init__(self, author_id, author, library_path):
		Source.__init__(self, author)
		self.library_path = library_path
		self.author_id = author_id

	def repr_key(self):
		return (self.library_path, self.author_id)

	def get_items(self):
		return get_books_from_library_by_author(self.library_path,
				self.author_id)

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield BookLeaf


class SeriesContentSource(Source):
	def __init__(self, series_id, name, library_path):
		Source.__init__(self, name)
		self.library_path = library_path
		self.series_id = series_id

	def repr_key(self):
		return (self.library_path, self.series_id)

	def get_items(self):
		return get_books_from_library_by_series(self.library_path,
				self.series_id)

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield BookLeaf


class AllBooksSource(Source, FilesystemWatchMixin):
	def __init__(self):
		Source.__init__(self, name=_("Calibre Books"))

	def initialize(self):
		dirs = []
		hist_file_path = os.path.expanduser(_HISTORY_FILE)
		if os.path.exists(hist_file_path):
			dirs.append(os.path.dirname(hist_file_path))
		dirs.extend(get_libraries())
		if dirs:
			self.monitor_token = self.monitor_directories(*dirs)

	def monitor_include_file(self, gfile):
		return gfile and gfile.get_basename() in ('history.plist', 'global.py',
				_METADATA_FILE)

	def get_description(self):
		return "All Calibre Books"

	def get_items(self):
		for library in get_libraries():
			for book in get_books_from_library(library):
				yield book

	def should_sort_lexically(self):
		return True

	def provides(self):
		yield BookLeaf


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
		yield SourceLeaf(AllBooksSource())
		yield SourceLeaf(AuthorsSource())
		yield SourceLeaf(SeriesSource())
		for library in get_libraries():
			yield SourceLeaf(LibraryBooksSource(library))

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


class AuthorsSource(Source, FilesystemWatchMixin):
	def __init__(self, library=None, name=_("Calibre Authors")):
		Source.__init__(self, name)
		self.library = library

	def initialize(self):
		if self.library:
			return
		dirs = _get_dirs_to_monitor()
		if dirs:
			self.monitor_token = self.monitor_directories(*dirs)

	def get_items(self):
		if self.library:
			for author in get_authors_from_library(self.library):
				yield author
		else:
			for library in get_libraries():
				for author in get_authors_from_library(library):
					yield author

	def repr_key(self):
		return repr(self.library)


class SeriesSource(Source, FilesystemWatchMixin):
	def __init__(self, library=None, name=_("Calibre Series")):
		Source.__init__(self, name)
		self.library = library

	def initialize(self):
		if self.library:
			return
		dirs = _get_dirs_to_monitor()
		if dirs:
			self.monitor_token = self.monitor_directories(*dirs)

	def get_items(self):
		if self.library:
			for series in get_series_from_library(self.library):
				yield series
		else:
			for library in get_libraries():
				for series in get_series_from_library(library):
					yield series

	def repr_key(self):
		return repr(self.library)
