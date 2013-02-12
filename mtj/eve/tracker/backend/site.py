import zope.component
import zope.interface

from zope.component.interfaces import IComponentLookup, ISite
from zope.component.globalregistry import BaseGlobalComponents
from zope.component.hooks import getSite, setSite


class BaseSite(object):
    """
    For a segregated installation.
    """

    zope.interface.implements(ISite)

    def __init__(self, sitemanager=None):
        if sitemanager is None:
            sitemanager = BaseGlobalComponents()
        self.setSiteManager(sitemanager)

    def __conform__(self, interface):
        if interface.isOrExtends(IComponentLookup):
            return self.getSiteManager()

    def setSiteManager(self, sitemanager):
        self._sitemanager = sitemanager

    def getSiteManager(self):
        return self._sitemanager
