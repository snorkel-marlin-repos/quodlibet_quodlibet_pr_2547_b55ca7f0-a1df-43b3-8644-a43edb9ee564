# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from __future__ import absolute_import

from quodlibet.compat import PY2
from .misc import get_ca_file

if PY2:
    import urllib2 as request_module
else:
    from urllib import request as request_module


Request = request_module.Request

urlopen = request_module.urlopen
# For general error handling use EnvironmentError


def install_urllib2_ca_file():
    """Makes urllib2.urlopen and urllib2.build_opener use the ca file
    returned by get_ca_file()
    """

    try:
        import ssl
    except ImportError:
        return

    base = request_module.HTTPSHandler

    class MyHandler(base):

        def __init__(self, debuglevel=0, context=None):
            ca_file = get_ca_file()
            if context is None and ca_file is not None:
                context = ssl.create_default_context(
                    purpose=ssl.Purpose.SERVER_AUTH,
                    cafile=ca_file)
            base.__init__(self, debuglevel, context)

    request_module.HTTPSHandler = MyHandler
