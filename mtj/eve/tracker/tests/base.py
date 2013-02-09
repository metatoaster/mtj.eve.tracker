import zope.component
from zope.component.hooks import setSite, setHooks
from zope.component.globalregistry import BaseGlobalComponents

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.backend.site import BaseSite
from mtj.eve.tracker.backend.sql import SQLAlchemyBackend


def buildSite():
    sm = BaseGlobalComponents()
    site = BaseSite(sm)
    return site

def setUp(suite):
    site = buildSite()
    sm = site.getSiteManager()
    setHooks()
    setSite(site)
    backend = SQLAlchemyBackend()
    sm.registerUtility(backend, ITrackerBackend)
