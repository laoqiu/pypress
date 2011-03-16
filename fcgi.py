#!/usr/bin/env python
from pypress import create_app

app = create_app('config.cfg')

from flup.server.fcgi import WSGIServer
WSGIServer(app,bindAddress='/tmp/pypress.sock').run()
