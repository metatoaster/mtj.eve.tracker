from __future__ import absolute_import
import functools

import evelink.api
from evelink.cache.sqlite import SqliteCache

import mtj.eve.tracker.evelink

_evelink_api_auto_api = evelink.api.auto_api


class EvelinkCache(object):
    """
    """

    _cache_path = None
    _cache = None
    _api = None


def auto_api(func):
    """Override for evelink's auto_api

    This allows automatic injection of the above persistent cache
    without users being aware.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'api' not in kwargs:
            if EvelinkCache._cache is None:
                # original function
                kwargs['api'] = evelink.api.API()
            else:
                kwargs['api'] = EvelinkCache._api
        return func(*args, **kwargs)
    return wrapper

def set_evelink_cache(path):
    """Globally enable caching with this sqlite path

    This initializes a SqliteCache for the evelink API wrapper, and
    monkey patches the auto_api decorator to make use of this cache.
    """

    EvelinkCache._cache_path = path
    EvelinkCache._cache = SqliteCache(path)
    api = mtj.eve.tracker.evelink.API()
    EvelinkCache._api = api

    mtj.eve.tracker.evelink.Map.api = api
    mtj.eve.tracker.evelink.EVE.api = api
    mtj.eve.tracker.evelink.Server.api = api

    # While the decorator method can be overriden by monkey patching
    # like so,

    # setattr(evelink.api, 'auto_api', auto_api)

    # However, if other bits of code might import things that call that
    # decorator first, the original init methods will not be effected
    # because the original was already called.
    #
    # Honestly, a more pragmatic solution is to submit a patch to the
    # main evelink project to modify the wrapper call to set the correct
    # instance to call.
    #
    # Of course we still have to deal with multithreaded cache access...

def unset_evelink_cache():
    EvelinkCache._cache_path = None
    EvelinkCache._cache = None
    EvelinkCache._api = None

    # setattr(evelink.api, 'auto_api', _evelink_api_auto_api)
