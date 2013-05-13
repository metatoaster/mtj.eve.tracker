from __future__ import absolute_import

from time import time, strftime, gmtime
from datetime import timedelta
from evelink import constants
import json
import zope.component

from mtj.f3u1.units import Time
from mtj.evedb.structure import ControlTower
from mtj.eve.tracker.interfaces import ITrackerBackend, ITowerManager


class Json(object):
    """
    Takes a backend object and generate JSON.

    Methods provided will acquire information from the backend in JSON
    format.
    """

    def __init__(self, backend, manager):
        assert ITrackerBackend.providedBy(backend)
        assert ITowerManager.providedBy(manager)
        self._backend = backend
        self._manager = manager

    @property
    def fuel_names(self):
        if not hasattr(self, '_fuel_names'):
            ct = ControlTower()
            tower_resources = ct.getControlTowerResources()
            self._fuel_names = {
                v['resourceTypeID']: v['typeName'] for v in tower_resources
            }
        return self._fuel_names

    def overview(self, low_fuel=432000):
        # overview should be a brief # listing of various things, rather
        # than a listing of all the towers.
        timestamp, towers = self._towers()
        towers = towers.values()

        online = sorted(
            [tower for tower in towers if tower.get('state') == 4
                and tower.get('timeRemaining', 0) < low_fuel
                and tower.get('apiTimestamp')
            ],
            lambda x, y: cmp(x.get('timeRemaining'), y.get('timeRemaining'))
        )
        reinforced = sorted(
            [tower for tower in towers if tower.get('state') == 3
                and tower.get('apiTimestamp')
            ],
            lambda x, y: cmp(x.get('stateTimestamp'), y.get('stateTimestamp'))
        )

        result = {
            'timestamp': timestamp,
            'online': online,
            'reinforced': reinforced,
        }
        return json.dumps(result)

    def _towers(self):
        timestamp = int(time())
        api_ts = self._manager.getTowerApiTimestamp
        tower_labels = self._backend.getAuditForTable('tower')

        def getLabel(id_):
            labels = tower_labels.get(id_, [])
            for label in labels:
                if label.category_name == 'label':
                    return label.reason
            return ''

        all_towers = {
            v.id: {
                'id': v.id,
                'apiTimestamp': api_ts(v.id),
                'apiTimestampFormatted': api_ts(v.id) is not None and
                        strftime('%Y-%m-%d %H:%M', gmtime(api_ts(v.id)))
                        or '',
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
                'stateTimestamp': v.stateTimestamp,
                'stateTimestampFormatted': strftime(
                    '%Y-%m-%d %H:%M',
                    gmtime(v.stateTimestamp)
                ),
                'stateTimestampDeltaFormatted':
                    str(timedelta(seconds=(v.stateTimestamp - timestamp))),
                'timeRemaining': v.getTimeRemaining(timestamp),
                'timeRemainingFormatted':
                    str(timedelta(seconds=v.getTimeRemaining(timestamp))),
                'auditLabel': getLabel(v.id),
            # FIXME using private _towers.
            } for v in self._backend._towers.values()}
        return timestamp, all_towers

    def towers(self):
        result = dict(zip(['timestamp', 'towers'], self._towers()))
        return json.dumps(result)

    def _audits(self, obj, rowid):
        all_audits = self._backend.getAuditEntry(obj, rowid)
        return {
            category_name: [
                {
                    'reason': v.reason,
                    'user': v.user,
                    'timestamp': v.timestamp,
                    'timestampFormatted':
                        strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
                }
                for v in audits
            ] for category_name, audits in all_audits.iteritems()
        }

    def audits(self, obj, rowid):
        audits = self._backend.getAuditEntriesFor(obj, rowid)
        result = {
            'audits': [{
                'category_name': v.category_name,
                'reason': v.reason,
                'user': v.user,
                'timestamp': v.timestamp,
                'timestampFormatted':
                    strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
            } for v in audits]
        }
        return json.dumps(result)

    def audits_recent(self, count=50):
        audits = self._backend.getAuditEntriesRecent(count)
        result = {
            'audits': [{
                'table': v.table,
                'rowid': v.rowid,
                'category_name': v.category_name,
                'reason': v.reason,
                'user': v.user,
                'timestamp': v.timestamp,
                'timestampFormatted':
                    strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
            } for v in audits]
        }
        return json.dumps(result)

    def tower(self, tower_id=None):
        if tower_id is None:
            return self.towers()

        backend = self._backend
        timestamp = int(time())
        api_ts = self._manager.getTowerApiTimestamp

        tower = backend.getTower(tower_id, None)
        if tower is None:
            return json.dumps({
                'error': 'Tower not found'
            })

        tower_log = backend.getTowerLog(tower_id, 10)
        tower_log_json = [{
            'id': v.id,
            'state': v.state,
            'stateName': constants.Corp.pos_states[v.state],
            'timestamp': v.timestamp,
            'timestampFormatted':
                strftime('%Y-%m-%d %H:%M:%S', gmtime(v.timestamp)),
            'stateTimestamp': v.stateTimestamp,
            'stateTimestampFormatted':
                strftime('%Y-%m-%d %H:%M:%S', gmtime(v.stateTimestamp)),
        } for v in tower_log]

        fuel_log = backend.getFuelLog(tower_id, 10)
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
            'apiTimestamp': api_ts(tower.id),
            'apiTimestampFormatted': api_ts(tower.id) is not None and
                    strftime('%Y-%m-%d %H:%M', gmtime(api_ts(tower.id)))
                    or '',
            'celestialName': tower.celestialName,
            'regionName': tower.regionName,
            'typeName': tower.typeName,
            'onlineSince': tower.onlineTimestamp,
            'onlineSinceFormatted': tower.onlineTimestamp and
                strftime('%Y-%m-%d %H:%M', gmtime(tower.onlineTimestamp)) or
                    'N/A',
            'offlineAt': tower.getOfflineTimestamp(),
            'offlineAtFormatted': tower.getOfflineTimestamp() and strftime(
                '%Y-%m-%d %H:%M', gmtime(tower.getOfflineTimestamp())) or
                    'N/A',
            'state': tower.getState(timestamp),
            'stateName': constants.Corp.pos_states[tower.getState(timestamp)],
            'stateTimestamp': tower.stateTimestamp,
            'stateTimestampFormatted': strftime(
                '%Y-%m-%d %H:%M',
                gmtime(tower.stateTimestamp)
            ),
            'stateTimestampDeltaFormatted':
                str(timedelta(seconds=(tower.stateTimestamp - timestamp))),
            'reinforcementLength': tower.getReinforcementLength(),
            'reinforcementLengthFormatted': str(Time('hour',
                second=tower.getReinforcementLength())),
            'timeRemaining': tower.getTimeRemaining(timestamp),
            'timeRemainingFormatted':
                str(timedelta(seconds=tower.getTimeRemaining(timestamp))),
            'audits': self._audits('tower', tower.id),
        }

        fuels = tower.getResources(timestamp)
        fuel_ratio = tower.getIdealFuelRatio()
        fuel_targets = tower.getIdealFuelingAmount(timestamp)

        fuel_json = [{
            'fuelId': k,
            'fuelName': self.fuel_names.get(k, ''),
            # TODO upstream needs to make this less ugly to acquire
            'delta': getattr(tower.fuels.get(k, None), 'delta', 0),
            'value': v,
            'optimalValue': fuel_ratio.get(k, 0),
            'missingValue': fuel_targets.get(k, 0),
        } for k, v in fuels.iteritems()]

        result = {
            'timestamp': timestamp,
            'tower': tower_json,
            'tower_log': tower_log_json,
            'fuel': fuel_json,
            'fuel_log': fuel_log_json,
        }
        return json.dumps(result)
