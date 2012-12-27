"""
A wrapper around some evelink classes

This module instantiates classes in evelink that has the `api` argument
as optional and provides an object for use.
"""

from __future__ import absolute_import

import itertools

import evelink

Map = evelink.map.Map()
EVE = evelink.eve.EVE()
Server = evelink.server.Server()

class API(evelink.api.API):
    def __init__(self, *a, **kw):
        if len(a) < 2 and not 'cache' in kw:
            from mtj.eve.tracker.cache import EvelinkCache
            kw['cache'] = EvelinkCache._cache
        return super(API, self).__init__(*a, **kw)


class Helper(object):
    """
    API helper class

    Provides some methods that helps with providing data from the API to
    the pos tracker.
    """

    _alliances = None
    _corporations = None
    _sov = None

    def __init__(self):
        pass

    def refresh(self):
        Helper._alliances = None
        Helper._corporations = None
        Helper._sov = None

    @property
    def alliances(self):
        if not Helper._alliances:
            Helper._alliances = EVE.alliances()
        return Helper._alliances

    @property
    def corporations(self):
        if not Helper._corporations:
            Helper._corporations = dict(itertools.chain(*[
                    [(j, i[0]) for j in i[1]['member_corps']]
                for i in self.alliances.iteritems()]))

        return Helper._corporations

    @property
    def sov(self):
        if not Helper._sov:
            Helper._sov, Helper._sov_timestamp = Map.sov_by_system()
        return Helper._sov
