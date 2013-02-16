import time

import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, Float, MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import zope.interface

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker import pos


Base = declarative_base()

# Backend has these tables
# tower
#     The actual towers.  Also log every change.
# fuel
#     For the fuels.
# silo
#     For the abstract silo contents.
# audit
#     For logging of audit actions, note down who did what.


class Tower(Base, pos.Tower):
    __tablename__ = 'tower'

    id = Column(Integer, primary_key=True)

    itemID = Column(Integer)
    typeID = Column(Integer)
    locationID = Column(Integer)
    moonID = Column(Integer)
    state = Column(Integer)
    stateTimestamp = Column(Integer)
    onlineTimestamp = Column(Integer)
    standingOwnerID = Column(Integer)

    def __init__(self, *a, **kw):
        pos.Tower.__init__(self, *a, **kw)


class TowerLog(object):
    # See SQLAlchemyBackend.addTower
    __tablename__ = 'tower_log'

    id = Column(Integer, primary_key=True)

    towerID = Column(Integer)
    itemID = Column(Integer)
    # typeID should be updated in parent when it becomes available.
    state = Column(Integer)
    stateTimestamp = Column(Integer)
    onlineTimestamp = Column(Integer)
    standingOwnerID = Column(Integer)


class Fuel(Base):
    __tablename__ = 'fuel'

    id = Column(Integer, primary_key=True)

    # this is the _internal_ id, not the one derived from the API as the
    # pos tracker can and should be able to be operated manually apart
    # from the API.
    towerID = Column(Integer)

    fuelTypeID = Column(Integer)
    delta = Column(Integer)
    timestamp = Column(Integer)
    # purpose is omitted as it is derived.
    value = Column(Integer)
    # resourceTypeName can be derived.
    # unitVolume can be derived.
    # freeze is generally 
    #freeze = Column(Boolean)

    def __init__(self, towerID, fuelTypeID, delta, timestamp, value):

        self.towerID = towerID
        self.fuelTypeID = fuelTypeID
        self.delta = delta
        self.timestamp = timestamp
        self.value = value


class Silo(Base):
    __tablename__ = 'silo'

    id = Column(Integer, primary_key=True)

    tower = Column(Integer)
    # typeName can be derived.
    # unitVolume can be derived.
    # volume can be derived.
    products = Column(String(255))  # string list representation?
    reactants = Column(String(255))  # string list representation?
    online = Column(Boolean)

    value = Column(Integer)
    full = Column(Integer)
    timestamp = Column(Integer)
    delta = Column(Integer)


#class Reaction(Base):
#    # As standard DBMS cannot handle simple lists of values like an
#    # object based db.  However above workaround can "solve" this.
#
#    __tablename__ = 'reaction'
#
#    id = Column(Integer, primary_key=True)
#
#    towerid = Column(Integer)
#    product = Column(Integer)
#    reactant = Column(Integer)


class Audit(Base):
    __tablename__ = 'audit'

    id = Column(Integer, primary_key=True)

    user = Column(String(255))
    table = Column(String(255))
    rowid = Column(Integer)
    reason = Column(String(255))
    timestamp = Column(Integer)

    def __init__(self, user, table, rowid, reason, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())

        self.user = user
        self.table = table
        self.rowid = rowid
        self.reason = reason
        self.timestamp = timestamp


class SQLAlchemyBackend(object):
    """
    SQLAlchemy based backend.

    Default is SQLite memory.

    A low level example usage for future reference::

        >>> from mtj.eve.tracker.backend.sql import SQLAlchemyBackend
        >>> from mtj.eve.tracker.backend.sql import Audit
        >>> bn = SQLAlchemyBackend()
        >>> session = bn.session()
        >>> audit = Audit('user', 'silo', 24, 'this is a test', 1359350165)
        >>> session.add(audit)
        >>> session.commit()
        >>> list(bn._conn.execute('select * from audit'))
        [(1, u'user', u'silo', 24, u'this is a test', 1359350165)]
    """

    zope.interface.implements(ITrackerBackend)

    def __init__(self, src=None):
        if not src:
            src = 'sqlite://'

        self._conn = create_engine(src)
        self._metadata = MetaData()
        self._metadata.reflect(bind=self._conn)
        Base.metadata.create_all(self._conn)
        self._sessions = sessionmaker(bind=self._conn)

    def session(self):
        return self._sessions()

    def addTower(self, *a, **kw):
        """
        Add a tower.

        Doesn't actually set a tower to some state, just append for now
        to log all changes made to a tower.
        """

        # A better plan may be this: have a table that maps internal ID
        # with the API one, and the timestamps and other related fields
        # be maintained separately from it.  For now this will do for a
        # basic demo of just the fuel tracking.

        tower = Tower(*a, **kw)
        session = self.session()
        session.add(tower)
        session.commit()

        return tower

    def updateTower(self, tower):
        pass

    def addFuel(self, tower=None, fuelTypeID=None, delta=None, timestamp=None,
            value=None, *a, **kw):

        towerID = tower.id
        fuel = Fuel(towerID, fuelTypeID, delta, timestamp, value)

        session = self.session()
        session.add(fuel)
        session.commit()

        return fuel
