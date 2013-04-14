from __future__ import absolute_import

import json
import zope.component

from flask import Blueprint, Flask, make_response

from mtj.eve.tracker.interfaces import ITrackerBackend, ITowerManager
from mtj.eve.tracker.frontend.json import Json


json_frontend = Blueprint('json_frontend', 'mtj.eve.tracker.frontend.flask')

@json_frontend.route('/overview')
def overview():
    backend = zope.component.getUtility(ITrackerBackend)
    manager = zope.component.getUtility(ITowerManager)
    jst = Json(backend, manager)
    result = jst.overview()
    response = make_response(result)
    response.headers['Content-type'] = 'application/json'
    return response

@json_frontend.route('/tower')
def towers():
    backend = zope.component.getUtility(ITrackerBackend)
    manager = zope.component.getUtility(ITowerManager)
    jst = Json(backend, manager)
    result = jst.towers()
    response = make_response(result)
    response.headers['Content-type'] = 'application/json'
    return response

@json_frontend.route('/tower/<int:tower_id>')
def tower(tower_id):
    backend = zope.component.getUtility(ITrackerBackend)
    manager = zope.component.getUtility(ITowerManager)
    jst = Json(backend, manager)
    result = jst.tower(tower_id)
    response = make_response(result)
    response.headers['Content-type'] = 'application/json'
    return response

@json_frontend.route('/update')
def update():
    """
    Need to figure out how to trigger the update from here without
    having a thread in here blocking for a while.

    We could just spawn a site based on that and then have it probe for
    updates periodically which is triggered in another thread/process
    above the one that is running flask.  So if API queries were to
    happen it should not affect the running flask instance.

    In that case, have this write a value somewhere.
    """

    return ''
