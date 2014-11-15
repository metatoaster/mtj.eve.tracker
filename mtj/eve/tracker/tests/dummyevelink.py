from __future__ import absolute_import

import time
import json
import itertools
from collections import OrderedDict
import zope.interface
from evelink.api import APIError
from evelink.api import APIResult

from mtj.eve.tracker.interfaces import IAPIHelper
from mtj.eve.tracker.interfaces import IAPIKeyManager

def mkresult(result):
    return APIResult(result['results'],
        result['last_timestamps']['current_time'],
        result['last_timestamps']['cached_until'],
    )


class DummyCorp(object):
    """
    Dummy Corp data provider.
    """

    starbases_index = 0
    starbase_details_index = 0

    def __init__(self, api=None):
        self.api = api
        if api is None:
            self.api = type('DummyAPI', (object,), {
                'api_key': (1, 'vcode')})()

    def _dummy_starbases(self):
        return OrderedDict(sorted(
            dummy_starbases[self.starbases_index].items()))

    def starbases(self):
        return mkresult(self._dummy_starbases())

    def _dummy_starbase_details(self):
        return OrderedDict(sorted(
            dummy_starbase_details[self.starbase_details_index].items()))

    def starbase_details(self, itemID):
        all_results = self._dummy_starbase_details()
        results = all_results.get(itemID, {})
        if results.get('results'):
            return mkresult(results)
        # pretend this is a bad itemID, as there can be condition where
        # the starbases list is returned from cache (because :ccp:) and
        # the actual starbase could have been taken down and repackaged
        # (or even destroyed).
        ts = results.get('last_timestamps', {}
            ).get('current_time', time.time())
        raise APIError(114, 'Invalid itemID provided.', ts)


class JsonDummyCorp(DummyCorp):
    """
    A dummy that uses a JSON encoded string as data source.

    This data source can be generated from live data using a valid API
    object using the dumps staticmethod, like so::

        from mtj.eve.tracker import evelink
        api = evelink.API(api_key=('123', 'someverifiercode'))
        corp = evelink.Corp(api)
        result_jstr = JsonDummyCorp.dumps(corp)
    """

    def loads(self, s):
        result = json.loads(s)

        # force certain ids back into int as json assume all keys are
        # strings.
        result['starbases']['results'] = {int(k): v
            for k, v in result['starbases']['results'].iteritems()}

        for k, v in result['starbase_details'].items():
            v['results']['fuel'] = {int(f): l
                for f, l in v['results']['fuel'].iteritems()}

        result['starbase_details'] = {int(k): v
            for k, v in result['starbase_details'].iteritems()}

        self._values = result

    def _dummy_starbases(self):
        return self._values['starbases']

    def _dummy_starbase_details(self):
        return self._values['starbase_details']

    @staticmethod
    def dumps(corp):
        result = corp.starbases()
        starbases = result.result
        corp_dump = {
            'starbases': {
                'results': starbases,
                'last_timestamps': {
                    'current_time': result.timestamp,
                    'cached_until': result.expires,
                }
            },
            'starbase_details': {},
        }
        sbd = {}
        for i in starbases.keys():
            try:
                result = corp.starbase_details(i)
                sd = {
                    'results': result.result,
                    'last_timestamps': {
                        'current_time': result.timestamp,
                        'cached_until': result.expires,
                    },
                }
            except APIError, e:
                continue
            sbd[i] = sd
        corp_dump['starbase_details'] = sbd
        return json.dumps(corp_dump)


@zope.interface.implementer(IAPIKeyManager)
class DummyKeyManager(object):
    def __init__(self):
        self.dummy = DummyCorp()

    def getAllWith(self, dummy):
        return [self.dummy]


@zope.interface.implementer(IAPIHelper)
class DummyHelper(object):
    """
    Dummy API Helper.

    Provides access to the dummy data below this class definition.
    """

    # the data indexes for the dynamic data tests.
    alliances_index = 0
    sov_index = 0

    def __init__(self):
        self.refresh()

    def refresh(self):
        self._alliances = None
        self._corporations = None
        self._sov = None

    @property
    def alliances(self):
        if self._alliances is None:
            self._alliances = dummy_alliances[self.alliances_index]
        return self._alliances

    @property
    def corporations(self):
        if self._corporations is None:
            self._corporations = dict(itertools.chain(*[
                    [(j, i[0]) for j in i[1]['member_corps']]
                for i in self.alliances.iteritems()]))
        return self._corporations

    @property
    def sov(self):
        if self._sov is None:
            self._sov = dummy_sov[self.sov_index]
        return self._sov

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
        'last_timestamps': {
            'current_time': 1362792986, 'cached_until': 1362793351},
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

    {
        'last_timestamps': {
            'current_time': 1362792986, 'cached_until': 1362793351},
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

            507863: {
                'itemID': 507863,
                'typeID': 20062,
                'standingOwnerID': 498125261,
                'stateTimestamp': None,
                'state': 1,
                'onlineTimestamp': None,
                'locationID': 30002904,
                'moonID': 40184218,
            },

        },
    },

    {
        'last_timestamps': {
            'current_time': 1362828986, 'cached_until': 1362829351},
        'results': {

            507862: {
                'itemID': 507862,
                'typeID': 20064,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1362901009,
                'state': 3,
                'onlineTimestamp': 1317198658,
                'locationID': 30004608,
                'moonID': 40291202,
            },

            507863: {
                'itemID': 507863,
                'typeID': 20062,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1362829986,
                'state': 4,
                'onlineTimestamp': 1362109986,
                'locationID': 30002904,
                'moonID': 40184218,
            },

        },
    },

    {
        'last_timestamps': {
            'current_time': 1363188986, 'cached_until': 1363189351},
        'results': {

            507862: {
                'itemID': 507862,
                'typeID': 20064,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1363261009,
                'state': 4,
                'onlineTimestamp': 1362901009,
                'locationID': 30004751,
                'moonID': 40291202,
            },

            507863: {
                'itemID': 507863,
                'typeID': 20062,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1363189986,
                'state': 4,
                'onlineTimestamp': 1362109986,
                'locationID': 30002904,
                'moonID': 40300804,
            },

        },
    },

    {
        'last_timestamps': {
            'current_time': 1363260409, 'cached_until': 1363264009},
        'results': {

            507862: {
                'itemID': 507862,
                'typeID': 20064,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1363261009,
                'state': 4,
                'onlineTimestamp': 1362901009,
                'locationID': 30004751,
                'moonID': 40291202,
            },

            507863: {
                'itemID': 507863,
                'typeID': 20062,
                'standingOwnerID': 498125261,
                'stateTimestamp': 1363909986,
                'state': 0,
                'onlineTimestamp': 0,
                'locationID': None,
                'moonID': None,
            },

        },
    },

]

dummy_starbase_details = [
    {
        507862: {
            'results': {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1362793009,
                u'fuel': {16275: 2250, 4312: 4027},
            },
            'last_timestamps': {
                'current_time': 1362792986,
                'cached_until': 1362793351,
            },
        },
    },

    {
        507862: {
            'results': {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1362829009,
                u'fuel': {16275: 2250, 4312: 3939},
            },
            'last_timestamps': {
                'current_time': 1362829863,
                'cached_until': 1362830462,
            },
        },
    },

    {
        507862: {
            'results': {
                u'online_ts': 1317197424,
                u'state': u'reinforced',
                u'state_ts': 1362901009,
                u'fuel': {4312: 3939},
            },
            'last_timestamps': {
                'current_time': 1362865863,
                'cached_until': 1362866462,
            },
        },

        507863: {
            'results': {
                u'online_ts': 1362109986,
                u'state': u'online',
                u'state_ts': 1362868609,
                u'fuel': {16275: 1000, 4051: 3939},
            },
            'last_timestamps': {
                'current_time': 1362865863,
                'cached_until': 1362866462,
            },
        },

    },

    {
        507862: {
            'results': {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1363261009,
                u'fuel': {16275: 3000, 4312: 6000},
            },
            'last_timestamps': {
                'current_time': 1363225863,
                'cached_until': 1363226462,
            },
        },

        507863: {
            'results': {
                u'online_ts': 1362109986,
                u'state': u'online',
                u'state_ts': 1363228609,
                u'fuel': {16275: 1000, 4051: 6000},
            },
            'last_timestamps': {
                'current_time': 1363225863,
                'cached_until': 1363226462,
            },
        },

    },

    {
        507862: {
            'results': {
                u'online_ts': 1317197424,
                u'state': u'online',
                u'state_ts': 1363261009,
                u'fuel': {16275: 2250, 4312: 4027},
            },
            'last_timestamps': {
                'current_time': 1363260409,
                'cached_until': 1363264009,
            },
        },
    },

    {
        507862: {
            'last_timestamps': {
                'current_time': 1363260409,
                'cached_until': 1363264009,
            },
        },

        507863: {
            'results': {
                u'online_ts': 1362109986,
                u'state': u'online',
                u'state_ts': 1363261009,
                u'fuel': {16275: 2000, 4051: 6000},
            },
            'last_timestamps': {
                'current_time': 1363260409,
                'cached_until': 1363264009,
            },
        },
    },

]
