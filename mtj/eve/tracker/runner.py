"""
The mtj eve tracker control module.

This probably could be placed in a separate egg.
"""

import logging

import zope.component
from zope.component.hooks import setSite, setHooks

from mtj.evedb.core import init_db, Db

from mtj.eve.tracker import evelink
from mtj.eve.tracker import interfaces
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend, SQLAPIKeyManager
from mtj.eve.tracker.manager import TowerManager, APIKeyManager

logger = logging.getLogger('mtj.eve.tracker.runner')


class BaseRunner(object):
    """
    The base runner for the tracker.
    """

    def __init__(self):
        self.site = BaseSite()
        self.sitemanager = self.site.getSiteManager()
        self.has_db = False
        setHooks()

    def configure(self, config):
        """
        Verify and set the base environment using the config.  No data
        loading or API calls should be made.
        """

        self.config = config

        # Logging related settings.
        s_logging = config.get('logging', {})
        log_level = s_logging.get('level', 'WARNING')
        log_format = s_logging.get('format',
            '%(asctime)s %(levelname)s %(name)s %(message)s')
        time_format = s_logging.get('time_format', '%Y-%m-%d %H:%M:%S')
        log_path = s_logging.get('path', '')

        # data
        s_paths = config.get('data', {})
        evelink_cache = s_paths.get('evelink_cache', ':memory:')
        evedb_url = s_paths.get('evedb_url', None)
        backend_url = s_paths.get('backend_url', 'sqlite:///:memory:')

        # api
        s_api = config.get('api', {})
        api_src = s_api.get('source', 'config')
        api_keys = s_api.get('api_keys', {})

        # set up the logging.

        formatter = logging.Formatter(log_format, time_format)
        if log_path:
            handler = logging.FileHandler(log_path)
        else:
            handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)

        if log_path is None:
            logger.info('Logging to stdout')

        # initialize the evedb
        if evedb_url:
            try:
                init_db(evedb_url)
            except:
                logger.exception('Fail to initialize evedb with the provided '
                                 'data.evedb_url [%s].', evedb_url)
            db = Db()
            self.has_db = db.hasTables('dgmTypeAttributes',
                'invControlTowerResources', 'invTypes', 'mapDenormalize',
                'mapSolarSystems')
        else:
            logger.critical('No data.evedb_url provided')

        if self.has_db is False:
            logger.critical('Incomplete or no evedb is present, pos tracker '
                            'WILL fail.')

        self._registerSite(evelink_cache, backend_url, api_src, api_keys)

    def _registerSite(self, evelink_cache, backend_url, api_src, api_keys):
        # set the site and then register the utilities

        setSite(self.site)
        sitemanager = self.sitemanager

        # first the cache as others will depend on this.
        cache = evelink.EvelinkSqliteCache(evelink_cache)
        sitemanager.registerUtility(cache, interfaces.IEvelinkCache)

        helper = evelink.Helper()
        sitemanager.registerUtility(helper, interfaces.IAPIHelper)

        backend = SQLAlchemyBackend(backend_url)
        sitemanager.registerUtility(backend, interfaces.ITrackerBackend)

        tower_manager = TowerManager(backend)
        sitemanager.registerUtility(tower_manager, interfaces.ITowerManager)

        # default key manager, always registered.
        key_manager = APIKeyManager(api_keys=api_keys)
        sitemanager.registerUtility(key_manager, interfaces.IAPIKeyManager)

        if api_src == 'backend':
            # alternatively provide the adapter for the key manager if
            # configured as such. 
            sitemanager.registerAdapter(SQLAPIKeyManager,
                required=(interfaces.ITrackerBackend,),
                provided=interfaces.IAPIKeyManager,
            )

    def initialize(self):
        """
        Load various core data into the tracker.
        """

        manager = zope.component.queryUtility(interfaces.ITowerManager)
        if manager is None:
            raise TypeError('No manager is registered.  Site not registered?')

        logger.info('%s starting up', self.__class__.__name__)
        logger.info('Instantiating towers from database.')
        manager.backend.reinstantiate()

    def run(self):
        raise NotImplementedError


class FlaskRunner(BaseRunner):
    """
    Runs a Flask app.
    """

    # note: local imports are used here to avoid direct dependency on
    # flask, as the flask specific modules here are provided for
    # convenience

    def prepare(self, app):
        prefix = self.config['mtj.eve.tracker.runner.FlaskRunner'].get(
            'json_prefix')
        if prefix:
            from mtj.eve.tracker.frontend.flask import json_frontend
            app.config['MTJPOSTRACKER_JSON_PREFIX'] = prefix
            app.register_blueprint(json_frontend, url_prefix=prefix)
        else:
            logger.info('No json_prefix defined; tracker will not serve JSON.')

        app.config['MTJPOSTRACKER_ADMIN_KEY'] = self.config[
            'mtj.eve.tracker.runner.FlaskRunner'].get('admin_key')

    def run(self, app=None):
        """
        Run the flask app.
        """

        if not app:
            import flask
            app = flask.Flask(__name__)

        self.prepare(app)

        host = self.config['flask']['host']
        port = self.config['flask']['port']
        # must be casted into a string.
        app.config['SECRET_KEY'] = str(self.config['flask']['secret'])
        app.run(host=host, port=port)
