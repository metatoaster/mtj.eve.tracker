"""
A wrapper around some evelink classes

This module instantiates classes in evelink that has the `api` argument
as optional and provides an object for use.
"""

from __future__ import absolute_import
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
