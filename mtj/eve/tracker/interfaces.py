import zope.interface


class IEvelinkCache(zope.interface.Interface):
    """
    Interface for our evelink cache utility.
    """


class IAPIHelper(zope.interface.Interface):
    """
    Interface for the API helper.
    """


class IHistorian(zope.interface.Interface):
    """
    The historian tracks transactions made and provides methods that
    interacts with the logged data.
    """


class ITrackerBackend(zope.interface.Interface):
    """
    Interface for the pos tracker backend.
    """
