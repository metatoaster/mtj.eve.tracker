from __future__ import absolute_import

import json
import zope.component

from flask import Flask

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.frontend.json import Json


app = Flask('mtj.eve.tracker.frontend.flask')

@app.route('/')
def index():
    return json.dumps(['overview'])

@app.route('/overview')
def overview():
    backend = zope.component.getUtility(ITrackerBackend)
    jst = Json(backend)
    return jst.overview()
