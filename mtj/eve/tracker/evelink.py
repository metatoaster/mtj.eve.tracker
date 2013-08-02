"""
A wrapper around some evelink classes

This module instantiates classes in evelink that has the `api` argument
as optional and provides an object for use.
"""

from __future__ import absolute_import

import itertools
from time import time

import zope.interface
import zope.component
import evelink
from evelink.cache.sqlite import SqliteCache

from mtj.eve.tracker.interfaces import IAPIHelper, IEvelinkCache


class API(evelink.api.API):
    def __init__(self, *a, **kw):
        if len(a) < 2 and not 'cache' in kw:
            kw['cache'] = zope.component.queryUtility(IEvelinkCache)
        return super(API, self).__init__(*a, **kw)


class Corp(evelink.corp.Corp):

    def starbases(self):
        """
        Copy of the parent, except state is not converted to string,
        and the keys are identical to the api.
        """
        api_result = self.api.get('corp/StarbaseList')

        rowset = api_result.find('rowset')
        results = {}
        for row in rowset.findall('row'):
            a = row.attrib
            starbase = {
                'itemID': int(a['itemID']),
                'typeID': int(a['typeID']),
                'locationID': int(a['locationID']),
                'moonID': int(a['moonID']),
                'state': int(a['state']),
                'stateTimestamp': evelink.api.parse_ts(a['stateTimestamp']),
                'onlineTimestamp': evelink.api.parse_ts(a['onlineTimestamp']),
                'standingOwnerID': int(a['standingOwnerID']),
            }
            results[starbase['itemID']] = starbase

        return results


class UtilityAPICache(evelink.api.APICache):
    """
    Provide them with the ability to make use of the registered cache
    utility it is available.
    """

    def _get_cache(self):
        cache_util = zope.component.queryUtility(IEvelinkCache)
        if cache_util:
            return cache_util
        return super(UtilityAPICache, self)

    def get(self, *a, **kw):
        return self._get_cache().get(*a, **kw)

    def put(self, *a, **kw):
        return self._get_cache().put(*a, **kw)


class EvelinkSqliteCache(SqliteCache):
    """
    For a zope component registered cache class extending from the
    default sqlite cache.
    """

    zope.interface.implements(IEvelinkCache)


class Helper(object):
    """
    API helper class

    Provides some methods that helps with providing data from the API to
    the pos tracker.
    """

    zope.interface.implements(IAPIHelper)

    api_cache = None

    # control internal refresh, to prevent polling the cache and/or make
    # api call.
    refresh_limit = 300  # 5 minutes
    refresh_time = 0

    def __init__(self):
        cache = zope.component.queryUtility(
            IEvelinkCache, default=UtilityAPICache())
        api = API(cache=cache)
        self.map = evelink.map.Map(api=api)
        self.eve = evelink.eve.EVE(api=api)
        self.refresh()

    def refresh(self):
        """
        Clears the cached results within the helper

        The next call will obviously get from the API.
        """

        if self.refresh_time + self.refresh_limit > time():
            return

        self.refresh_time = time()
        self._alliances = None
        self._corporations = None
        self._sov = None

    @property
    def alliances(self):
        if not self._alliances:
            self._alliances = self.eve.alliances()
        return self._alliances

    @property
    def corporations(self):
        if not self._corporations:
            self._corporations = dict(itertools.chain(*[
                    [(j, i[0]) for j in i[1]['member_corps']]
                for i in self.alliances.iteritems()]))

        return self._corporations

    @property
    def sov(self):
        if not self._sov:
            self._sov, self._sov_timestamp = self.map.sov_by_system()
        return self._sov
