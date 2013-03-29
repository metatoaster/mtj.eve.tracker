"""
The mtj eve tracker control module.

This probably could be placed in a separate egg.
"""

import logging

import zope.component
from zope.component.hooks import setSite, setHooks

from mtj.eve.tracker import evelink
from mtj.eve.tracker import interfaces
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend, SQLAPIKeyManager
from mtj.eve.tracker.manager import TowerManager, APIKeyManager

logger = logging.getLogger('mtj.eve.tracker.ctl')


class BaseRunner(object):
    """
    The base runner for the tracker.
    """

    def __init__(self):
        self.site = BaseSite()
        self.sitemanager = self.site.getSiteManager()
        setHooks()

    def initialize(self, config):
        setSite(self.site)

        # Logging related settings.
        s_logging = config.get('logging', {})
        log_level = s_logging.get('level', 'WARNING')
        log_format = s_logging.get('format',
            '%(asctime)s %(levelname)s %(name)s %(message)s')
        time_format = s_logging.get('time_format', '%Y-%m-%d %H:%M:%S')
        log_path = s_logging.get('path', None)

        # data
        s_paths = config.get('data', {})
        evelink_cache = s_paths.get('evelink_cache', ':memory:')
        backend_url = s_paths.get('backend_url', 'sqlite:///:memory:')

        # api
        s_api = config.get('api', {})
        api_src = s_api.get('source', 'config')
        api_keys = s_api.get('api_keys', [])

        sitemanager = self.sitemanager

        # set up the logging.

        formatter = logging.Formatter(log_format, time_format)
        if log_path is None:
            handler = logging.StreamHandler()
        else:
            handler = logging.FileHandler(log_path)
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)

        if log_path is None:
            logger.info('Logging to stdout')

        # register the utilities

        # first the cache as others will depend on this.
        cache = evelink.EvelinkSqliteCache(evelink_cache)
        sitemanager.registerUtility(cache, interfaces.IEvelinkCache)

        helper = evelink.Helper()
        sitemanager.registerUtility(helper, interfaces.IAPIHelper)

        backend = SQLAlchemyBackend(backend_url)
        sitemanager.registerUtility(backend, interfaces.ITrackerBackend)

        tower_manager = TowerManager(backend)
        sitemanager.registerUtility(tower_manager, interfaces.ITowerManager)

        key_manager = APIKeyManager(api_keys=api_keys)
        sitemanager.registerUtility(key_manager, interfaces.IAPIKeyManager)

        if api_src == 'backend':
            sitemanager.registerAdapter(SQLAPIKeyManager,
                required=(interfaces.ITrackerBackend,),
                provided=interfaces.IAPIKeyManager,
            )

    def start(self):
        logger.info('BaseRunner starting up')
        logger.info('Instantiating towers from database.')
        manager = zope.component.queryUtility(interfaces.ITowerManager)
        manager.backend.reinstantiate()
