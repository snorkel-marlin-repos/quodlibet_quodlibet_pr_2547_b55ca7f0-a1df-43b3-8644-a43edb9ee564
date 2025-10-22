# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import gettext
import locale

from senf import environ, path2fsn, fsn2text, text2fsn

from quodlibet.util.path import unexpand
from quodlibet.util.dprint import print_d
from quodlibet.compat import text_type, PY2, listfilter

from .misc import get_locale_encoding


def locale_format(format, val, *args, **kwargs):
    """Like locale.format but returns text"""

    result = locale.format(format, val, *args, **kwargs)
    if isinstance(result, bytes):
        result = result.decode(get_locale_encoding(), "replace")
    return result


def bcp47_to_language(code):
    """Takes a BCP 47 language identifier and returns a value suitable for the
    LANGUAGE env var.

    Only supports a small set of inputs and might return garbage..
    """

    if code == "zh-Hans":
        return "zh_CN"
    elif code == "zh-Hant":
        return "zh_TW"

    parts = code.split("-")
    is_iso = lambda s: len(s) == 2 and s.isalpha()

    # we only support ISO 639-1
    if not is_iso(parts[0]):
        return parts[0].replace(":", "")
    lang_subtag = parts[0]

    region = ""
    if len(parts) >= 2 and is_iso(parts[1]):
        region = parts[1]
    elif len(parts) >= 3 and is_iso(parts[2]):
        region = parts[2]

    if region:
        return "%s_%s" % (lang_subtag, region)
    return lang_subtag


def osx_locale_id_to_lang(id_):
    """Converts a NSLocale identifier to something suitable for LANG"""

    if not "_" in id_:
        return id_
    # id_ can be "zh-Hans_TW"
    parts = id_.rsplit("_", 1)
    ll = parts[0]
    ll = bcp47_to_language(ll).split("_")[0]
    return "%s_%s" % (ll, parts[1])


def set_i18n_envvars():
    """Set the LANG/LANGUAGE environment variables if not set in case the
    current platform doesn't use them by default (OS X, Window)
    """

    if os.name == "nt":
        from quodlibet.util.winapi import GetUserDefaultUILanguage, \
            GetSystemDefaultUILanguage

        langs = listfilter(None, map(locale.windows_locale.get,
                                     [GetUserDefaultUILanguage(),
                                      GetSystemDefaultUILanguage()]))
        if langs:
            environ.setdefault('LANG', langs[0])
            environ.setdefault('LANGUAGE', ":".join(langs))
    elif sys.platform == "darwin":
        from AppKit import NSLocale
        locale_id = NSLocale.currentLocale().localeIdentifier()
        lang = osx_locale_id_to_lang(locale_id)
        environ.setdefault('LANG', lang)

        preferred_langs = NSLocale.preferredLanguages()
        if preferred_langs:
            languages = map(bcp47_to_language, preferred_langs)
            environ.setdefault('LANGUAGE', ":".join(languages))
    else:
        return


def fixup_i18n_envvars():
    """Sanitizes env vars before gettext can use them.

    LANGUAGE should support a priority list of languages with fallbacks, but
    doesn't work due to "en" no being known to gettext (This could be solved
    by providing a en.po in QL but all other libraries don't define it either)

    This tries to fix that.
    """

    try:
        langs = environ["LANGUAGE"].split(":")
    except KeyError:
        return

    # So, this seems to be an undocumented feature where C selects
    # "no translation". Append it to any en/en_XX so that when not found
    # it falls back to "en"/no translation.
    sanitized = []
    for lang in langs:
        sanitized.append(lang)
        if lang.startswith("en") and len(langs) > 1:
            sanitized.append("C")

    environ["LANGUAGE"] = ":".join(sanitized)


class GlibTranslations(gettext.GNUTranslations):
    """Provide a glib-like translation API for Python.

    This class adds support for pgettext (and upgettext) mirroring
    glib's C_ macro, which allows for disambiguation of identical
    source strings. It also installs N_, C_, and ngettext into the
    __builtin__ namespace.

    It can also be instantiated and used with any valid MO files
    (though it won't be able to translate anything, of course).
    """

    def __init__(self, fp=None):
        self.path = (fp and fp.name) or ""
        self._catalog = {}
        self.plural = lambda n: n != 1
        gettext.GNUTranslations.__init__(self, fp)
        self._debug_text = None

    def ugettext(self, message):
        # force unicode here since __contains__ (used in gettext) ignores
        # our changed defaultencoding for coercion, so utf-8 encoded strings
        # fail at lookup.
        message = text_type(message)
        if PY2:
            return text_type(gettext.GNUTranslations.ugettext(self, message))
        else:
            return text_type(gettext.GNUTranslations.gettext(self, message))

    def ungettext(self, msgid1, msgid2, n):
        # see ugettext
        msgid1 = text_type(msgid1)
        msgid2 = text_type(msgid2)
        if PY2:
            return text_type(
                gettext.GNUTranslations.ungettext(self, msgid1, msgid2, n))
        else:
            return text_type(
                gettext.GNUTranslations.ngettext(self, msgid1, msgid2, n))

    def unpgettext(self, context, msgid, msgidplural, n):
        context = text_type(context)
        msgid = text_type(msgid)
        msgidplural = text_type(msgidplural)
        real_msgid = u"%s\x04%s" % (context, msgid)
        real_msgidplural = u"%s\x04%s" % (context, msgidplural)
        result = self.ngettext(real_msgid, real_msgidplural, n)
        if result == real_msgid:
            return msgid
        elif result == real_msgidplural:
            return msgidplural
        return result

    def upgettext(self, context, msgid):
        context = text_type(context)
        msgid = text_type(msgid)
        real_msgid = u"%s\x04%s" % (context, msgid)
        result = self.ugettext(real_msgid)
        if result == real_msgid:
            return msgid
        return result

    def set_debug_text(self, debug_text):
        self._debug_text = debug_text

    def wrap_text(self, value):
        if self._debug_text is None:
            return value
        else:
            return self._debug_text + value + self._debug_text

    def install(self, *args, **kwargs):
        raise NotImplementedError("We no longer do builtins")


_initialized = False
_debug_text = None
_translations = {
    "quodlibet": GlibTranslations(),
}


def set_debug_text(debug_text=None):
    """
    Args:
        debug_text (text_type or None): text to add to all translations
    """

    global _debug_text, _translations

    _debug_text = debug_text
    for trans in _translations.values():
        trans.set_debug_text(debug_text)


def register_translation(domain, localedir=None):
    """Register a translation domain

    Args:
        domain (str): the gettext domain
        localedir (pathlike): A directory used for translations, if it doesn't
            exist the system one will be used.
    Returns:
        GlibTranslations
    """

    global _debug_text, _translations, _initialized

    assert _initialized

    if localedir is not None and os.path.isdir(localedir):
        print_d("Using local localedir: %r" % unexpand(localedir))
        gettext.bindtextdomain(domain, localedir)

    localedir = gettext.bindtextdomain(domain)

    try:
        t = gettext.translation(domain, localedir, class_=GlibTranslations)
    except IOError:
        print_d("No translation found in %r" % unexpand(localedir))
        t = GlibTranslations()
    else:
        print_d("Translations loaded: %r" % unexpand(t.path))

    t.set_debug_text(_debug_text)
    _translations[domain] = t
    return t


def init(language=None):
    """Call this sometime at start before any register_translation()
    and before any gettext using libraries are loaded.

    Args:
        language (text_type or None): Either a language to use or None for the
            system derived default.
    """

    global _initialized

    set_i18n_envvars()
    fixup_i18n_envvars()

    print_d("LANGUAGE: %r" % environ.get("LANGUAGE"))
    print_d("LANG: %r" % environ.get("LANG"))

    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass

    # XXX: these are our most user facing APIs, make sre they are not loaded
    # before we set the language. For GLib this is too late..
    assert "gi.repository.Gtk" not in sys.modules
    assert "gi.repository.Gst" not in sys.modules

    if language is not None:
        environ["LANGUAGE"] = text2fsn(language)
        print_d("LANGUAGE: %r" % environ.get("LANGUAGE"))

    _initialized = True


def get_available_languages(domain):
    """Returns a list of available translations for a given gettext domain.

    Args:
        domain (str)
    Returns:
        List[text_type]
    """

    locale_dir = gettext.bindtextdomain(domain)
    if locale_dir is None:
        return []

    try:
        entries = os.listdir(locale_dir)
    except OSError:
        return []

    langs = [u"C"]
    for lang in entries:
        mo_path = os.path.join(
            locale_dir, lang, "LC_MESSAGES", "%s.mo" % domain)
        if os.path.exists(mo_path):
            langs.append(fsn2text(path2fsn(lang)))
    return langs


def _(message):
    """
    Args:
        message (text_type)
    Returns:
        text_type

    Lookup the translation for message
    """

    t = _translations["quodlibet"]
    return t.wrap_text(t.ugettext(message))


def N_(message):
    """
    Args:
        message (text_type)
    Returns:
        text_type

    Only marks a string for translation
    """

    return text_type(message)


def C_(context, message):
    """
    Args:
        context (text_type)
        message (text_type)
    Returns:
        text_type

    Lookup the translation for message for a context
    """

    t = _translations["quodlibet"]
    return t.wrap_text(t.upgettext(context, message))


def ngettext(singular, plural, n):
    """
    Args:
        singular (text_type)
        plural (text_type)
        n (int)
    Returns:
        text_type

    Returns the translation for a singular or plural form depending
    on the value of n.
    """

    t = _translations["quodlibet"]
    return t.wrap_text(t.ungettext(singular, plural, n))


def numeric_phrase(singular, plural, n, template_var=None):
    """Returns a final locale-specific phrase with pluralisation if necessary
    and grouping of the number.

    This is added to custom gettext keywords to allow us to use as-is.

    Args:
        singular (text_type)
        plural (text_type)
        n (int)
        template_var (text_type)
    Returns:
        text_type

    For example,

    ``numeric_phrase('Add %d song', 'Add %d songs', 12345)``
    returns
    `"Add 12,345 songs"`
    (in `en_US` locale at least)
    """
    num_text = locale_format('%d', n, grouping=True)
    if not template_var:
        template_var = '%d'
        replacement = '%s'
        params = num_text
    else:
        template_var = '%(' + template_var + ')d'
        replacement = '%(' + template_var + ')s'
        params = dict()
        params[template_var] = num_text
    return (ngettext(singular, plural, n).replace(template_var, replacement) %
            params)


def npgettext(context, singular, plural, n):
    """
    Args:
        context (text_type)
        singular (text_type)
        plural (text_type)
        n (int)
    Returns:
        text_type

    Like ngettext, but with also depends on the context.
    """

    t = _translations["quodlibet"]
    return t.wrap_text(t.unpgettext(context, singular, plural, n))
