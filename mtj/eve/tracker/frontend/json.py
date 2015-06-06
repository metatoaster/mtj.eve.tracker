from __future__ import absolute_import

import re
from operator import itemgetter
from time import time, strftime, gmtime
from datetime import timedelta
from evelink import constants
import json

from mtj.f3u1.units import Time
from mtj.evedb.structure import ControlTower
from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.backend.model import api_usage_states

# for case insensitive matching of '[ignore] in audit label.
is_ignored = re.compile('\\[ignore\\]', re.IGNORECASE).search

def format_ts(ts):
    return ts and strftime('%Y-%m-%d %H:%M', gmtime(ts)) or 'N/A'


class Json(object):
    """
    Takes a backend object and generate JSON.

    Methods provided will acquire information from the backend in JSON
    format.
    """

    def __init__(self, backend, manager=None):
        # XXX manager was required, I thought I might do submission and
        # updates but I decided against it.
        assert ITrackerBackend.providedBy(backend)
        self._backend = backend
        self.set_timestamp()

    def set_timestamp(self, timestamp=None):
        self.current_timestamp = timestamp or int(time())

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
                and not is_ignored(tower.get('auditLabel'))
            ], key=itemgetter('timeRemaining'),
        )
        reinforced = sorted(
            [tower for tower in towers if tower.get('state') == 3
                and tower.get('apiTimestamp')
            ], key=itemgetter('stateTimestamp'),
        )
        offlined = sorted(
            [tower for tower in towers if tower.get('state') == 1
                and tower.get('apiTimestamp')
                and not is_ignored(tower.get('auditLabel'))
            ], key=itemgetter('auditLabel'),
        )
        api_usage = self.api_usage()

        result = {
            'timestamp': timestamp,
            'api_usage': api_usage,
            'online': online,
            'reinforced': reinforced,
            'offlined': offlined,
        }
        return json.dumps(result)

    def api_usage(self):
        timestamp = self.current_timestamp
        return [{
            'start_ts': start_ts,
            'start_ts_delta': str(Time('second',
                second=(timestamp - start_ts))),
            'start_ts_formatted': format_ts(start_ts),
            'end_ts': end_ts,
            'end_ts_delta': end_ts and str(Time('second',
                second=(timestamp - end_ts))),
            'end_ts_formatted': format_ts(end_ts),
            'state': api_usage_states.get(s, 'unknown'),
        } for start_ts, end_ts, s in
            sorted(self._backend.currentApiUsage(timestamp=timestamp).values(),
                key=itemgetter(0))]

    def api_ts(self, tower_id):
        value = self._backend.getTowerApiTimestamp(tower_id)
        if not value:
            return {
                'apiTimestamp': None,
                'apiTimestampFormatted': '',
                'apiErrorCount': None,
            }
        return {
            'apiTimestamp': value.currentTime,
            'apiTimestampFormatted': format_ts(value.currentTime),
            'apiErrorCount': value.api_error_count,
        }

    def _towers(self):
        timestamp = self.current_timestamp
        tower_labels = self._backend.getAuditForTable('tower')

        def getLabel(id_):
            labels = tower_labels.get(id_, [])
            for label in labels:
                if label.category_name == 'label':
                    return label.reason
            return ''

        all_towers = {}
        # FIXME using private _towers.
        for v in self._backend._towers.values():
            tower = {
                'id': v.id,
                'celestialName': v.celestialName,
                'regionName': v.regionName,
                'typeID': v.typeID,
                'typeName': v.typeName,
                'offlineAt': v.getOfflineTimestamp(),
                'offlineAtFormatted': format_ts(v.getOfflineTimestamp()),
                'state': v.getState(timestamp),
                'stateName': constants.Corp.pos_states[v.getState(timestamp)],
                'stateTimestamp': v.stateTimestamp,
                'stateTimestampFormatted': format_ts(v.stateTimestamp),
                'stateTimestampDeltaFormatted':
                    str(timedelta(seconds=(v.stateTimestamp - timestamp))),
                'timeRemaining': v.getTimeRemaining(timestamp),
                'timeRemainingFormatted':
                    str(timedelta(seconds=v.getTimeRemaining(timestamp))),
                'auditLabel': getLabel(v.id),
            }
            tower.update(self.api_ts(v.id))
            all_towers[v.id] = tower
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
                    'timestampFormatted': format_ts(v.timestamp),
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
                'timestampFormatted': format_ts(v.timestamp),
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
                'timestampFormatted': format_ts(v.timestamp),
            } for v in audits]
        }
        return json.dumps(result)

    def tower(self, tower_id=None):
        if tower_id is None:
            return self.towers()

        backend = self._backend
        timestamp = self.current_timestamp

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
            'timestampFormatted': format_ts(v.timestamp),
            'stateTimestamp': v.stateTimestamp,
            'stateTimestampFormatted': format_ts(v.stateTimestamp),
        } for v in tower_log]

        fuel_log = backend.getFuelLog(tower_id, 10)
        fuel_log_json = [{
            'id': v.id,
            'fuelId': v.fuelTypeID,
            'fuelName': self.fuel_names.get(v.fuelTypeID, ''),
            'value': v.value,
            'delta': v.delta,
            'timestamp': v.timestamp,
            'timestampFormatted': format_ts(v.timestamp),
        } for v in fuel_log]

        tower_json = {
            'id': tower.id,
            'celestialName': tower.celestialName,
            'regionName': tower.regionName,
            'typeName': tower.typeName,
            'onlineSince': tower.onlineTimestamp,
            'onlineSinceFormatted': format_ts(tower.onlineTimestamp),
            'offlineAt': tower.getOfflineTimestamp(),
            'offlineAtFormatted': format_ts(tower.getOfflineTimestamp()),
            'state': tower.getState(timestamp),
            'stateName': constants.Corp.pos_states[tower.getState(timestamp)],
            'stateTimestamp': tower.stateTimestamp,
            'stateTimestampFormatted': format_ts(tower.stateTimestamp),
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
        tower_json.update(self.api_ts(tower.id))

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
        } for k, v in sorted(fuels.iteritems())]

        result = {
            'timestamp': timestamp,
            'tower': tower_json,
            'tower_log': tower_log_json,
            'fuel': fuel_json,
            'fuel_log': fuel_log_json,
        }
        return json.dumps(result)
