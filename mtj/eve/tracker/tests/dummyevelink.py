from __future__ import absolute_import

import time
import itertools
import zope.interface
from evelink.api import APIError

from mtj.eve.tracker.interfaces import IAPIHelper


class DummyCorp(object):
    """
    Dummy Corp data provider.
    """

    starbases_index = 0
    starbase_details_index = 0

    def __init__(self, api=None):
        self.api = api
        if api is None:
            self.api = type('DummyAPI', (object,), {})()

    def starbases(self):
        results = dummy_starbases[self.starbases_index]
        # XXX "set" api timestamp
        self.api.last_timestamps = results['_timestamps']
        return results['results']

    def starbase_details(self, itemID):
        results = dummy_starbase_details[self.starbase_details_index]
        all_details = results['results']
        result = all_details.get(itemID, None)
        if result:
            self.api.last_timestamps = results['_timestamps']
            return result
        # pretend this is a bad itemID, as there can be condition where
        # the starbases list is returned from cache (because :ccp:) and
        # the actual starbase could have been taken down and repackaged
        # (or even destroyed).
        ts = time.time()
        raise APIError(114, 'Invalid itemID provided.', (ts, ts))


class DummyHelper(object):
    """
    Dummy API Helper.

    Provides access to the dummy data below this class definition.
    """

    zope.interface.implements(IAPIHelper)

    # the data indexes for the dynamic data tests.
    alliances_index = 0
    sov_index = 0

    def __init__(self):
        pass

    def refresh(self):
        pass

    @property
    def alliances(self):
        return dummy_alliances[self.alliances_index]

    @property
    def corporations(self):
        return dict(itertools.chain(*[
                [(j, i[0]) for j in i[1]['member_corps']]
            for i in self.alliances.iteritems()]))

    @property
    def sov(self):
        return dummy_sov[self.sov_index]

dummy_alliances = [
    {
        1354830081: {
            'executor_id': 1344654522,
            'id': 1354830081,
            'member_corps': {
                109788662: {'id': 109788662, 'timestamp': 1275525120},
                667531913: {'id': 667531913, 'timestamp': 1275612900},
                725842137: {'id': 725842137, 'timestamp': 1275602100},
                1063360566: {'id': 1063360566, 'timestamp': 1275525120},
                1184675423: {'id': 1184675423, 'timestamp': 1275525120},
                1344654522: {'id': 1344654522, 'timestamp': 1275620100},
            },
            'member_count': 8931,
            'name': 'Goonswarm Federation',
            'ticker': 'CONDI',
            'timestamp': 1275370560,
        },

        498125261: {
            'executor_id': 416584095,
            'id': 498125261,
            'member_corps': {
                  98007599: {'id': 98007599, 'timestamp': 1295398080},
                  98007654: {'id': 98007654, 'timestamp': 1306916760},
                  98054999: {'id': 98054999, 'timestamp': 1311780300},
                  98091273: {'id': 98091273, 'timestamp': 1355033940},
                  320162553: {'id': 320162553, 'timestamp': 1273973280},
                  416584095: {'id': 416584095, 'timestamp': 1273698300},
                  1018389948: {'id': 1018389948, 'timestamp': 1273794780},
            },
            'member_count': 11317,
            'name': 'Test Alliance Please Ignore',
            'ticker': 'TEST',
            'timestamp': 1273698300,
        }
    },

    {
        1354830081: {
            'executor_id': 1344654522,
            'id': 1354830081,
            'member_corps': {
                109788662: {'id': 109788662, 'timestamp': 1275525120},
                667531913: {'id': 667531913, 'timestamp': 1275612900},
                725842137: {'id': 725842137, 'timestamp': 1275602100},
                1063360566: {'id': 1063360566, 'timestamp': 1275525120},
                1184675423: {'id': 1184675423, 'timestamp': 1275525120},
                1344654522: {'id': 1344654522, 'timestamp': 1275620100},
            },
            'member_count': 8931,
            'name': 'Goonswarm Federation',
            'ticker': 'CONDI',
            'timestamp': 1275370560,
        },

        498125261: {
            'executor_id': 416584095,
            'id': 498125261,
            'member_corps': {
                  98007599: {'id': 98007599, 'timestamp': 1295398080},
                  98007654: {'id': 98007654, 'timestamp': 1306916760},
                  98054999: {'id': 98054999, 'timestamp': 1311780300},
                  98091273: {'id': 98091273, 'timestamp': 1355033940},
                  320162553: {'id': 320162553, 'timestamp': 1273973280},
                  416584095: {'id': 416584095, 'timestamp': 1273698300},
                  # kick b0rt
            },
            'member_count': 6917,
            'name': 'Test Alliance Please Ignore',
            'ticker': 'TEST',
            'timestamp': 1273698300,
        }
    },
]

dummy_sov = [
    {
        30002904: {'alliance_id': 1354830081, 'corp_id': 1344654522,
                  'faction_id': None, 'id': 30002904, 'name': 'VFK-IV'},
        30004267: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004267, 'name': 'Nema'},
        30004268: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004268, 'name': 'Shenda'},
        30004608: {'alliance_id': 498125261, 'corp_id': 1018389948,
                  'faction_id': None, 'id': 30004608, 'name': '6VDT-H'},
        30004751: {'alliance_id': 498125261, 'corp_id': 1018389948,
                  'faction_id': None, 'id': 30004751, 'name': 'K-6K16'},
    },

    {
        30002904: {'alliance_id': 1354830081, 'corp_id': 1344654522,
                  'faction_id': None, 'id': 30002904, 'name': 'VFK-IV'},
        30004267: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004267, 'name': 'Nema'},
        30004268: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004268, 'name': 'Shenda'},
        30004608: {'alliance_id': None, 'corp_id': None,  # kartoon'd
                  'faction_id': None, 'id': 30004608, 'name': '6VDT-H'},
        30004751: {'alliance_id': 498125261, 'corp_id': 1018389948,
                  'faction_id': None, 'id': 30004751, 'name': 'K-6K16'},
    },

    {
        30002904: {'alliance_id': 498125261, 'corp_id': 1018389948,  # by march
                  'faction_id': None, 'id': 30002904, 'name': 'VFK-IV'},
        30004267: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004267, 'name': 'Nema'},
        30004268: {'alliance_id': None, 'corp_id': None,
                  'faction_id': 500003, 'id': 30004268, 'name': 'Shenda'},
        30004608: {'alliance_id': 498125261, 'corp_id': 1018389948,
                  'faction_id': None, 'id': 30004608, 'name': '6VDT-H'},
        30004751: {'alliance_id': 498125261, 'corp_id': 1018389948,
                  'faction_id': None, 'id': 30004751, 'name': 'K-6K16'},
    },
]

dummy_starbases = [
    {
        '_timestamps': (1362792986, 1362793351),
        'results': {
            507862: {
                'itemID': 507862,
                'typeID': 20064,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1362793009,
                'state': 4,
                'onlineTimestamp': 1317198658,
                'locationID': 30004608,
                'moonID': 40291202,
            },
        },
    },
]

dummy_starbase_details = [
    {
        '_timestamps': (1362792986, 1362793351),
        'results': {
            507862: {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1362793009,
                u'fuel': {16275: 2250, 4312: 4027},
            },
        },
    },

    {
        '_timestamps': (1362829863, 1362830462),
        'results': {
            507862: {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1362829009,
                u'fuel': {16275: 2250, 4312: 3939},
            },
        },
    },
]
