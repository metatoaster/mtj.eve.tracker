"""
The mtj eve tracker control module.

This probably could be placed in a separate egg.
"""

import logging
import time
import importlib
from functools import partial

try:
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop
    from tornado.ioloop import PeriodicCallback
    HAS_TORNADO = True
except ImportError:
    HAS_TORNADO = False

try:
    from concurrent.futures import ThreadPoolExecutor
    HAS_FUTURES = True
except ImportError:
    HAS_FUTURES = False

import zope.component
from zope.component.hooks import setSite, setHooks, getSite

from mtj.evedb.core import init_db, Db

from mtj.eve.tracker import evelink
from mtj.eve.tracker import interfaces
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend, SQLAPIKeyManager
from mtj.eve.tracker.manager import TowerManager, APIKeyManager

logger = logging.getLogger('mtj.eve.tracker.runner')

# the default timer for all background tasks.
PULSE = 13000  # microseconds
MAX_WORKERS = 2


class BaseRunner(object):
    """
    The base runner for the tracker.
    """

    site = None

    def __init__(self,
            pulse=PULSE,
            max_workers=MAX_WORKERS,
        ):
        self.has_db = False
        setHooks()
        self.updater = None

        self._next_run = {}
        # schedule_map key is settings.key
        self.schedule_map = {
            'import_frequency':
                ('manager_importAll', self.manager_importAll,
                    self.manager_importAll_callback),
            # "safe" version
            # 'import_frequency':
            #     ('manager_importAll', self.manager_importAll_safe,
            #         self.manager_importAll_safe_callback),
        }
        self.running = set()

        self.pulse = pulse
        self.max_workers = max_workers

        if HAS_FUTURES:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

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

    def _registerSite(self, site=None):
        # set the site and then register the utilities from self.config

        if site is None:
            site = self.site

        setSite(site)
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

    # XXX both of these are BAD for different reasons, but if we want to
    # do in-process updates in background, the current design calls for
    # this.  Better way would have a backend-only thread and the front-
    # end thread will fetch data from there into a cache if possible,
    # and if it can't (due to the running update locking things) present
    # the data from the cache.
    # 
    # Now for the methods - the _safe methods are more pedantic, in the
    # sense that updates are done and fetch completely in a background
    # thread so that the foreground thread (the one running the IOLoop)
    # won't have access to the that until the callback is called, which
    # the future will contain the new TrackerBackend and that will be
    # tossed into the for use.
    # 
    # The second one is the less careful one, where we set that thread
    # to use the same site (ZCA does use thread-locals carefully but we
    # are totally violating that here) and then updates are applied
    # directly to the objects in the TrackerBackend.  Nothing should go
    # wrong as there are nothing else that will manipulate the Tower
    # related objects... we are using that first.
    #
    # End of the day though is that both are bad because it breaks
    # threading conventions.  Especially in sqlalchemy where it warns
    # about cross-thread things...
    #
    # Lastly, I think I need to break this up properly into real server-
    # client components.

    def manager_importAll_safe(self):
        # The proper way to do this should be giving this thread locals
        # its own personal instance, so rebuild the whole thing if the
        # site does not validate...

        try:
            self.validateSite()
        except:  # ComponentLookupError
            # register a whole new set of component for a new site.
            site = BaseSite()
            setSite(site)
            self._registerSite(site)
            backend = zope.component.getUtility(interfaces.ITrackerBackend)
            backend.reinstantiate()
        
        # Here everything is normal.
        manager = zope.component.getUtility(interfaces.ITowerManager)
        manager.importAll()

        # For the callback to function as intended, the backend with the
        # data needs to be returned, and then nuke the site that we just
        # built completely before returning that.
        
        backend = zope.component.getUtility(interfaces.ITrackerBackend)
        setSite()
        return backend

    def manager_importAll_safe_callback(self, future):
        # If we were to do this thread-safety pedantically, we will take
        # the backend returned and set that as the new one.
        # 
        new_backend = future.result()
        if not interfaces.ITrackerBackend.providedBy(new_backend):
            logger.error(
                'manager_importAll did not result in a new tower backend?')
            return
        
        old_backend = zope.component.getUtility(interfaces.ITrackerBackend)
        
        sitemanager = getSite().getSiteManager()
        sitemanager.unregisterUtility(old_backend, interfaces.ITrackerBackend)
        sitemanager.registerUtility(new_backend, interfaces.ITrackerBackend)

    def manager_importAll(self):
        # However, since only the stuff in the TowerManager will be
        # touched and there isn't anything anywhere else that will write
        # to things inside it (yet) so this shortcut will be taken.

        setSite(self.site)

        # Here everything is normal.
        manager = zope.component.getUtility(interfaces.ITowerManager)
        manager.importAll()

    def manager_importAll_callback(self, future):
        # Since we already updated everything in-place.
        return

    def pulse_run(self, task_label, method):
        try:
            logger.info('Task `%s` running in thread executor.', task_label)
            return method()
        except:
            logger.exception('Error running task `%s`', task_label)
            raise

    def pulse_task_done(self,
            period_key, task_label, callback=None, future=None):
        logger.info('Task `%s` completed.', task_label)
        self.running.discard(period_key)
        if callback:
            logger.info('Calling Task `%s` callback.', task_label)
            callback(future)

    def pulse_timer(self, timestamp=None):
        if not timestamp:
            timestamp = time.time()

        settings = zope.component.getUtility(interfaces.ISettingsManager)
        for period_key, method_callback in self.schedule_map.items():
            task_label, method, callback = method_callback

            period = getattr(settings, period_key, None)
            if not isinstance(period, int):
                logger.error('settings.%s must be an integer', period_key)
                continue

            if self._next_run.get(period_key, 0) > timestamp:
                logger.debug('Task `%s` is not ready to run yet.', task_label)
                continue

            if period_key in self.running:
                logger.warning('Task `%s` is marked as running, ignored.',
                               task_label)
                continue

            # mark running task and set the time it can be called again.
            self.running.add(period_key)
            self._next_run[period_key] = timestamp + period

            task = self._executor.submit(self.pulse_run, task_label, method)
            # XXX this is why we need tornado
            task.add_done_callback(
                lambda future: IOLoop.instance().add_callback(
                    partial(self.pulse_task_done,
                        period_key, task_label, callback, future))
            )


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

        if HAS_TORNADO:
            if HAS_FUTURES:
                logger.info('Threadpool available, automatic update enabled.')
                callback = PeriodicCallback(self.pulse_timer, self.pulse)
                callback.start()
            else:
                logger.warning('The `concurrent.futures` module unavailable, '
                    'please install the `futures` package if automatic update '
                    'of data is desired.')
            http_server = HTTPServer(WSGIContainer(app))
            http_server.listen(port)
            logger.info('tornado.httpserver listening on port %s', port)
            logger.info('Starting tornado.ioloop.')
            try:
                IOLoop.instance().start()
            except KeyboardInterrupt:
                return
        else:
            # is this really needed if all we are using tornado is for
            # the async stuff?  Could have the threadpool run the
            # background schedule thread perhaps?
            logger.warning('Using default Werkzeug server; '
                           'automatic update will not be enabled.')
            app.run(host=host, port=port)
