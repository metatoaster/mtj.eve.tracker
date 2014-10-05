import zope.interface


class IEvelinkCache(zope.interface.Interface):
    """
    Interface for our evelink cache utility.
    """


class IAPIHelper(zope.interface.Interface):
    """
    Interface for the API helper.
    """


class IAPIKeyManager(zope.interface.Interface):
    """
    Interface for the API key manager.
    """


class IHistorian(zope.interface.Interface):
    """
    The historian tracks transactions made and provides methods that
    interacts with the logged data.
    """


class ISettingsManager(zope.interface.Interface):
    """
    Settings manager.
    """


class ITrackerBackend(zope.interface.Interface):
    """
    Interface for the pos tracker backend.
    """


class ITowerManager(zope.interface.Interface):
    """
    Interface for the tower manager.

    Implementation of this class deals with linking various bits of data
    together, such as the EVE API.
    """
