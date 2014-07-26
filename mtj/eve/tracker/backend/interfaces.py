from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker.interfaces import IAPIKeyManager


class ISQLAPIKeyManager(IAPIKeyManager):
    """
    SQLAlchemy version of API key manager.
    """


class ISQLAlchemyBackend(ITrackerBackend):
    """
    SQLALchemy version of the tracker backend.
    """
