import zope.component
from zope.component.hooks import setSite, setHooks, getSiteManager

from mtj.eve.tracker.interfaces import IAPIHelper, ITrackerBackend
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend

from mtj.eve.tracker.tests.dummyevelink import DummyHelper


def setUp(suite, backend=None, helper=None):
    installTestSite()
    registerBackend(backend)
    registerHelper(helper)

def tearDown(suite):
    setSite()

def installTestSite():
    site = BaseSite()
    sm = site.getSiteManager()
    setHooks()
    setSite(site)

def registerBackend(backend=None):
    # The basic memory based backend.
    if backend is None:
        backend = SQLAlchemyBackend()
    sm = getSiteManager()
    sm.registerUtility(backend, ITrackerBackend)

def registerHelper(helper=None):
    # set up the helper
    if helper is None:
        helper = DummyHelper()
    sm = getSiteManager()
    sm.registerUtility(helper, IAPIHelper)
