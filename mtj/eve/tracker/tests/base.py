import zope.component
from zope.component.hooks import setSite, setHooks

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend


def setUp(suite):
    site = BaseSite()
    sm = site.getSiteManager()
    setHooks()
    setSite(site)

    # The basic memory based backend.
    backend = SQLAlchemyBackend()
    sm.registerUtility(backend, ITrackerBackend)
