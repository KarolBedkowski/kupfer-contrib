# -*- coding: UTF-8 -*-

__kupfer_name__ = _("Calibre")
__kupfer_sources__ = ("LibrariesSource", "AllBooksSource", "AuthorsSource",
                      "SeriesSource")
__kupfer_actions__ = ("OpenLibrary", "AddToLibrary")
__description__ = _("Book in Calibre Library")
__version__ = "2017-02-07"
__author__ = "Karol Będkowski <karol.bedkowski@gmail.com>"
'''
Changes:
	2013-08-08: init
	2013-10-14: read libraries from gui.json
		+OpenLibrary, AddToLibrary actions
	2017-02-07: update to Kupfer v300+; Python3
'''

import os
import sqlite3
from contextlib import closing

try:
    import cjson
    json_decoder = cjson.decode
except ImportError:
    import json
    json_decoder = json.loads

from kupfer import utils
from kupfer.objects import Source, FileLeaf, Leaf, SourceLeaf, Action
from kupfer.obj.helplib import FilesystemWatchMixin
from kupfer.obj.apps import AppLeafContentMixin
from kupfer.obj.fileactions import Open

_HISTORY_FILE = '~/.config/calibre/history.plist'
_GUI_JSON_FILE = '~/.config/calibre/gui.json'
_METADATA_FILE = 'metadata.db'
_CALIBRE_GLOBAL = '~/.config/calibre/global.py'
_EBOOK_EXTENSIONS = ('epub', 'pdf', 'mobi', 'prc', 'txt', 'doc', 'rtf', 'html',
                     'chm')


def get_libraries():
    gui_json_file = os.path.expanduser(_GUI_JSON_FILE)
    if not os.path.isfile(gui_json_file):
        return
    with open(gui_json_file) as f:
        root = json_decoder(f.read())
        if not root:
            return
    library_usage_stats = root.get('library_usage_stats')
    if library_usage_stats:
        for library in library_usage_stats.keys():
            if os.path.exists(library):
                yield library


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
            if default_book:
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
    def __init__(self, default_book, book_id, title, author, path,
                 metadata_file):
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


class LibraryLeaf(Leaf):
    def __init__(self, library_path):
        Leaf.__init__(self, library_path, os.path.split(library_path)[-1])

    def get_description(self):
        return _("Library: %s") % self.object


class SimpleLibrariesSource(Source):
    def __init__(self):
        Source.__init__(self, _("Calibre Libraries"))

    def get_items(self):
        for library in get_libraries():
            yield LibraryLeaf(library)


class LibraryBooksSource(Source):
    def __init__(self, library_path):
        Source.__init__(self, os.path.basename(library_path))
        self.library_path = library_path

    def get_description(self):
        return "Calibre Library %s" % self.name

    def repr_key(self):
        return self.library_path

    def get_items(self):
        yield SourceLeaf(
            AuthorsSource(
                self.library_path, name=_("<Calibre Authors>")))
        yield SourceLeaf(
            SeriesSource(
                self.library_path, name=_("<Calibre Series>")))
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


class LibrariesSource(AppLeafContentMixin, Source, FilesystemWatchMixin):
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
                yield FileLeaf(
                    os.path.join(self.path, name + "." + format_.lower()))

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


class OpenLibrary(Action):
    """ Open Calibre Library"""

    def __init__(self):
        Action.__init__(self, _("Open in Calibre"))

    def activate(self, leaf):
        utils.spawn_async(
            ["calibre", "--with-library=" + str(leaf.object.library_path)])

    def item_types(self):
        yield SourceLeaf

    def valid_for_item(self, item):
        return isinstance(item.object, LibraryBooksSource)


class AddToLibrary(Action):
    """Add file to Calibre library."""

    def __init__(self):
        Action.__init__(self, _("Add to Calibre Library..."))

    def activate(self, leaf, iobj):
        utils.spawn_async(
            ["calibre", "--with-library=" + str(iobj.object), leaf.object])

    def requires_object(self):
        return True

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, item):
        ext = os.path.splitext(item.object)[-1]
        return ext and ext[1:] in _EBOOK_EXTENSIONS

    def object_source(self, for_item=None):
        return SimpleLibrariesSource()

    def object_types(self):
        yield LibraryLeaf
