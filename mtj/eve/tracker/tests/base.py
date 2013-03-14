import zope.component
from zope.component.hooks import setSite, setHooks, getSiteManager

from mtj.eve.tracker.interfaces import IAPIHelper, ITrackerBackend
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend

from mtj.eve.tracker.tests.dummyevelink import DummyHelper


def setUp(suite):
    installTestSite()
    registerBackend()
    registerHelper()

def tearDown(suite):
    setSite()

def installTestSite():
    site = BaseSite()
    sm = site.getSiteManager()
    setHooks()
    setSite(site)

def registerBackend():
    # The basic memory based backend.
    backend = SQLAlchemyBackend()
    sm = getSiteManager()
    sm.registerUtility(backend, ITrackerBackend)

def registerHelper():
    # set up the helper
    helper = DummyHelper()
    sm = getSiteManager()
    sm.registerUtility(helper, IAPIHelper)
