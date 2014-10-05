import zope.interface

from mtj.eve.tracker.interfaces import ISettingsManager


@zope.interface.implementer(ISettingsManager)
class BaseSettingsManager(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DefaultSettingsManager(BaseSettingsManager):
    pass
