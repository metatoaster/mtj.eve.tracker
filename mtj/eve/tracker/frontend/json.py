from __future__ import absolute_import

from time import time, strftime, gmtime
from datetime import timedelta
from evelink import constants
import json

from mtj.evedb.structure import ControlTower
from mtj.eve.tracker.interfaces import ITrackerBackend

from . import util


class Json(object):
    """
    Takes a backend object and generate JSON.

    Methods provided will acquire information from the backend in JSON
    format.
    """

    def __init__(self, backend):
        assert ITrackerBackend.providedBy(backend)
        self._backend = backend

    @property
    def fuel_names(self):
        if not hasattr(self, '_fuel_names'):
            ct = ControlTower()
            tower_resources = ct.getControlTowerResources()
            self._fuel_names = {
                v['resourceTypeID']: v['typeName'] for v in tower_resources
            }
        return self._fuel_names

    def overview(self):
        # overview should be a brief # listing of various things, rather
        # than a listing of all the towers.
        return self.towers()

    def towers(self):
        timestamp = int(time())
        test_json = {'towers': {
            v.id: {
                'id': v.id,
                'celestialName': v.celestialName,
                'regionName': v.regionName,
                'typeID': v.typeID,
                'typeName': v.typeName,
                'offlineAt': v.getOfflineTimestamp(),
                'offlineAtFormatted': strftime(
                    '%Y-%m-%d %H:%M',
                    gmtime(v.getOfflineTimestamp())
                ),
                'state': v.getState(timestamp),
                'stateName': constants.Corp.pos_states[v.getState(timestamp)],
                'timeRemaining': v.getTimeRemaining(timestamp),
                'timeRemainingFormatted':
                    str(timedelta(seconds=v.getTimeRemaining(timestamp))),
            # FIXME using private _towers.
            } for v in self._backend._towers.values()}}
        return json.dumps(test_json)

    def tower(self, tower_id=None):
        if tower_id is None:
            return self.towers()

        backend = self._backend
        timestamp = int(time())

        tower = backend.getTower(tower_id, None)
        if tower is None:
            return json.dumps({
                'error': 'Tower not found'
            })

        tower_log = backend.getTowerLog(tower_id)
        tower_log_json = [{
            'id': v.id,
            'state': v.state,
            'stateName': constants.Corp.pos_states[v.state],
            'timestamp': v.timestamp,
            'timestampFormatted':
                strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
        } for v in tower_log]

        fuel_log = backend.getFuelLog(tower_id)
        fuel_log_json = [{
            'id': v.id,
            'fuelId': v.fuelTypeID,
            'fuelName': self.fuel_names.get(v.fuelTypeID, ''),
            'value': v.value,
            'delta': v.delta,
            'timestamp': v.timestamp,
            'timestampFormatted':
                strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
        } for v in fuel_log]

        tower_json = {
            'id': tower.id,
            'celestialName': tower.celestialName,
            'regionName': tower.regionName,
            'typeName': tower.typeName,
            'onlineSince': tower.onlineTimestamp,
            'onlineSinceFormatted':
                strftime('%Y-%m-%d %H:%M', gmtime(tower.onlineTimestamp)),
            'offlineAt': tower.getOfflineTimestamp(),
            'offlineAtFormatted': strftime(
                '%Y-%m-%d %H:%M', gmtime(tower.getOfflineTimestamp())),
            'state': tower.getState(timestamp),
            'stateName': constants.Corp.pos_states[tower.getState(timestamp)],
            'reinforcementLength': tower.getReinforcementLength(),
            'reinforcementLengthFormatted': util.format_reinforcement(
                timedelta(seconds=tower.getReinforcementLength())),
            'timeRemaining': tower.getTimeRemaining(timestamp),
            'timeRemainingFormatted':
                str(timedelta(seconds=tower.getTimeRemaining(timestamp))),
        }

        fuels = tower.getResources(timestamp)

        fuel_json = [{
            'fuelId': k,
            'fuelName': self.fuel_names.get(k, ''),
            'value': v,
        } for k, v in fuels.iteritems()]

        result = {
            'tower': tower_json,
            'tower_log': tower_log_json,
            'fuel': fuel_json,
            'fuel_log': fuel_log_json,
        }
        return json.dumps(result)
