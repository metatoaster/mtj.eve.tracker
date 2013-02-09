import zope.interface


class IHistorian(zope.interface.Interface):
    """
    The historian tracks transactions made and provides methods that
    interacts with the logged data.
    """


class ITrackerBackend(zope.interface.Interface):
    """
    Interface for the pos tracker backend.
    """
