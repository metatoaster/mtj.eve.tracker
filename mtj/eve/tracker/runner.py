"""
The mtj eve tracker control module.

This probably could be placed in a separate egg.
"""

import logging
import importlib

import zope.component
from zope.component.hooks import setSite, setHooks, getSite

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

    site = None

    def __init__(self):
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
        evedb_url = s_paths.get('evedb_url', None)

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

    def _registerSite(self):
        # set the site and then register the utilities from self.config

        setSite(self.site)
        sitemanager = getSite().getSiteManager()

        # the list of required interfaces to register utilities for,
        # in the order they need to be done.
        interface_names = ['IEvelinkCache', 'IAPIHelper', 'ISettingsManager',
            'ITrackerBackend', 'ITowerManager', 'IAPIKeyManager',]

        implementations = self.config.get('implementations', {})

        # first the cache as others will depend on this.
        for ifacename in interface_names:
            impspec = implementations[ifacename]
            ns, clsname = impspec['class'].split(':')
            mod = importlib.import_module(ns)
            cls = getattr(mod, clsname)
            iface = getattr(interfaces, ifacename)
            obj = cls(*impspec['args'], **impspec['kwargs'])
            sitemanager.registerUtility(obj, iface)

    def validateSite(self):
        """
        Ensure all utilities are present and available.
        """

        sm = getSite().getSiteManager()
        # should probably use the keys defined in implementations
        # schema, but a little duplication here doesn't hurt for
        # validation.  Also see above method.
        cache = sm.getUtility(interfaces.IEvelinkCache)
        helper = sm.getUtility(interfaces.IAPIHelper)
        backend = sm.getUtility(interfaces.ITrackerBackend)
        tower_manager = sm.getUtility(interfaces.ITowerManager)
        key_manager = sm.getUtility(interfaces.IAPIKeyManager)
        settings = sm.getUtility(interfaces.ISettingsManager)

    def _preinitialize(self):
        # Thread-locals...
        if self.site is None:
            self.site = BaseSite()
        self._registerSite()
        self.validateSite()

    def initialize(self):
        """
        Load various core data into the tracker.
        """

        self._preinitialize()

        backend = zope.component.queryUtility(interfaces.ITrackerBackend)
        if backend is None:
            raise TypeError('No backend is registered.  Site not registered?')

        logger.info('%s starting up', self.__class__.__name__)
        logger.info('Instantiating towers from database.')
        backend.reinstantiate()

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

        try:
            from tornado.wsgi import WSGIContainer
            from tornado.httpserver import HTTPServer
            from tornado.ioloop import IOLoop
            http_server = HTTPServer(WSGIContainer(app))
            http_server.listen(port)
            logger.info('tornado.httpserver listening on port %s', port)
            try:
                logger.info('Starting tornado.ioloop.')
                IOLoop.instance().start()
            except KeyboardInterrupt:
                return
        except ImportError:
            app.run(host=host, port=port)
