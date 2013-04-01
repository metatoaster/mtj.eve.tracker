from __future__ import absolute_import

from time import time, strftime, gmtime
from evelink import constants
import json

from mtj.eve.tracker.interfaces import ITrackerBackend


class Json(object):
    """
    Takes a backend object and generate JSON.

    Methods provided will acquire information from the backend in JSON
    format.
    """

    def __init__(self, backend):
        assert ITrackerBackend.providedBy(backend)
        self._backend = backend

    def overview(self):
        timestamp = time()
        test_json = {
            v.id: {
                 'id': v.id,
                 'celestialName': v.celestialName,
                 'regionName': v.regionName,
                 'typeName': v.typeName,
                 'typeName': v.typeName,
                 'offlineAt': v.getOfflineTimestamp(),
                 'offlineAtFormatted': strftime(
                     '%Y-%m-%d:%H:%M',
                     gmtime(v.getOfflineTimestamp())
                 ),
                 'state': v.getState(timestamp),
                 'stateName': constants.Corp.pos_states[v.getState(timestamp)],
            # FIXME using private _towers.
            } for v in self._backend._towers.values()}
        return json.dumps(test_json)
