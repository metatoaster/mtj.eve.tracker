from __future__ import absolute_import

import json
import zope.component

from flask import Blueprint, Flask, make_response, current_app, request

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

@json_frontend.route('/audits_recent/', defaults={'count': 50})
@json_frontend.route('/audits_recent/<int:count>')
def audits_recent(count):
    backend = zope.component.getUtility(ITrackerBackend)
    manager = zope.component.getUtility(ITowerManager)
    jst = Json(backend, manager)
    result = jst.audits_recent(count)
    response = make_response(result)
    response.headers['Content-type'] = 'application/json'
    return response

@json_frontend.route('/audit/<table>/<int:rowid>')
def audit_tbl_rowid(table, rowid):
    backend = zope.component.getUtility(ITrackerBackend)
    manager = zope.component.getUtility(ITowerManager)
    jst = Json(backend, manager)
    result = jst.audits(table, rowid)
    response = make_response(result)
    response.headers['Content-type'] = 'application/json'
    return response

@json_frontend.route('/reload', methods=['POST'])
def reload_db():
    """
    Trigger a reload from db if the right keys are provided.
    """

    def process():
        admin_key = current_app.config.get('MTJPOSTRACKER_ADMIN_KEY')
        if not admin_key:
            return {'status': 'error', 'result':
                'reload not enabled; no admin key defined',
            }, 403
        try:
            # consider using request.json?
            data = json.loads(request.data)
            key = data.get('key')
        except:
            key = None

        if not (key and key == admin_key):
            return {'status': 'error', 'result':
                'invalid key',
            }, 403
        manager = zope.component.getUtility(ITowerManager)
        results = manager.refresh()
        return {'status': 'ok', 'result':
            '%d towers reloaded.' % results,
        }, None

    data, http_code = process()
    result = json.dumps(data)
    response = make_response(result, http_code)
    response.headers['Content-type'] = 'application/json'
    return response
