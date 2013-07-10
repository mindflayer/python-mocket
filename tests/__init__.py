from __future__ import unicode_literals
import sys
PY2 = sys.version_info[0] == 2

if PY2:
    from urllib2 import urlopen, HTTPError
else:
    from urllib.request import urlopen
    from urllib.error import HTTPError