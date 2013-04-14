import time
import logging

import sqlalchemy
from sqlalchemy import func, desc
from sqlalchemy import Column, Integer, String, Boolean, Float, MetaData, Text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

import zope.interface

from mtj.eve.tracker.interfaces import ITrackerBackend, IAPIKeyManager
from mtj.eve.tracker import pos
from mtj.eve.tracker import evelink


_marker = object()

Base = declarative_base()

logger = logging.getLogger('mtj.eve.tracker.backend.sql')

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

    itemID = Column(Integer, index=True)
    typeID = Column(Integer)
    locationID = Column(Integer)
    moonID = Column(Integer)
    state = Column(Integer)
    stateTimestamp = Column(Integer)
    onlineTimestamp = Column(Integer)
    standingOwnerID = Column(Integer)

    def __init__(self, *a, **kw):
        pos.Tower.__init__(self, *a, **kw)

    def _reloadResources(self, session):
        """
        Reload resources from database.
        """

        self.initResources()

        # load pos fuel info.
        # dict comprehension
        all_fuels = {v['resourceTypeID']: v for v in
            pos.pos_info.getControlTowerResource(self.typeID)}

        # query for stuff
        results = session.query(Fuel).filter(
            Fuel.tower_id == self.id).group_by(
                Fuel.fuelTypeID).having(func.max(Fuel.id))

        for result in results.all():
            resourceTypeID = result.fuelTypeID
            fuel = all_fuels.get(resourceTypeID)
            timestamp = self.resourcePulseTimestamp(result.timestamp)
            res_buffer = pos.TowerResourceBuffer(
                delta=result.delta,
                timestamp=timestamp,
                purpose=fuel['purpose'],
                value=result.value,
                resourceTypeName=fuel['typeName'],
                unitVolume=fuel['volume'],
            )
            self.fuels[resourceTypeID] = res_buffer


class TowerLog(Base):
    # See SQLAlchemyBackend.addTower
    __tablename__ = 'tower_log'

    id = Column(Integer, primary_key=True)

    tower_id = Column(Integer, index=True)

    itemID = Column(Integer)
    typeID = Column(Integer)
    locationID = Column(Integer)
    moonID = Column(Integer)
    state = Column(Integer)
    stateTimestamp = Column(Integer)
    onlineTimestamp = Column(Integer)
    standingOwnerID = Column(Integer)

    timestamp = Column(Integer, index=True)

    def __init__(self, tower_id, itemID, typeID, locationID, moonID, state,
            stateTimestamp, onlineTimestamp, standingOwnerID):

        self.tower_id = tower_id
        self.itemID = itemID
        self.typeID = typeID
        self.locationID = locationID
        self.moonID = moonID
        self.state = state
        self.stateTimestamp = stateTimestamp
        self.onlineTimestamp = onlineTimestamp
        self.standingOwnerID = standingOwnerID
        self.timestamp = int(time.time())


class TowerApi(Base):
    """
    For tracking API and Tower relationships.
    """

    __tablename__ = 'tower_api'

    # Not using itemID because it can be reused for a different tower.
    # tower_id is unique within the context of our tracker which is what
    # this tracker cares about.
    # Might be useful to have both, actually.
    tower_id = Column(Integer, primary_key=True)
    # Assuming to be integer.  If this requires nuking it's trivial to
    # regenerate this whole table.
    api_key = Column(Integer, index=True)
    currentTime = Column(Integer)
    timestamp = Column(Integer)

    def __init__(self, tower_id, api_key, currentTime):

        self.tower_id = tower_id
        self.api_key = api_key
        self.currentTime = currentTime
        # this may seem to duplicate above, but is useful to verify
        # the staleness of the data's currentTime.
        self.timestamp = int(time.time())


class Fuel(Base):
    __tablename__ = 'fuel'

    id = Column(Integer, primary_key=True)

    # this is the _internal_ id, not the one derived from the API as the
    # pos tracker can and should be able to be operated manually apart
    # from the API.
    tower_id = Column(Integer)

    fuelTypeID = Column(Integer)
    delta = Column(Integer)
    timestamp = Column(Integer, index=True)
    # purpose is omitted as it is derived.
    value = Column(Integer)
    # resourceTypeName can be derived.
    # unitVolume can be derived.
    # freeze is derived
    #freeze = Column(Boolean)

    def __init__(self, tower_id, fuelTypeID, delta, timestamp, value):

        self.tower_id = tower_id
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


class Category(Base):
    """
    Generic category system table.
    """

    __tablename__ = 'category'

    # type
    table = Column(String(255), primary_key=True)
    name = Column(String(255), primary_key=True)
    description = Column(Text)

    def __init__(self, table, name, description):
        self.table = table
        self.name = name
        self.description = description


class Audit(Base):
    """
    Auditing entries.

    This serves to annotate data entries present in this instance.

    Going for the lazy/naive approach of using natural keys (i.e.
    strings) for tracking who did what and what other notes might be.

    For fuels and silos, the person who did the task may annotate the
    relevant row with an audit entry as one is generated for every
    change.

    Other annotations for other tables like towers and names could mean
    naming a tower, or noting a tower as something to be tear down.
    """

    __tablename__ = 'audit'

    id = Column(Integer, primary_key=True)

    table = Column(String(255))
    rowid = Column(Integer)
    reason = Column(Text)
    user = Column(String(255))
    category_name = Column(String(255))
    timestamp = Column(Integer)

    def __init__(self, table, rowid, reason, user, name='', timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())

        self.table = table
        self.rowid = rowid
        self.reason = reason
        self.user = user
        self.category_name = name
        self.timestamp = timestamp


class APIKey(Base):

    __tablename__ = 'api_key'

    key = Column(String(255), primary_key=True)
    vcode = Column(String(255))

    def __init__(self, key, vcode):
        self.key = key
        self.vcode = vcode


class ApiUsageLog(Base):

    __tablename__ = 'api_usage_log'

    id = Column(Integer, primary_key=True)
    api_key = Column(Integer, index=True)
    state = Column(Integer)
    start_ts = Column(Integer, index=True)
    end_ts = Column(Integer)

    def __init__(self, api_key, start_ts=None):
        self.api_key = api_key
        self.start_ts = start_ts and start_ts or int(time.time())
        self.end_ts = None


class SQLAlchemyBackend(object):
    """
    SQLAlchemy based backend.

    Default is SQLite memory.

    A low level example usage for future reference::

        >>> from mtj.eve.tracker.backend.sql import SQLAlchemyBackend
        >>> from mtj.eve.tracker.backend.sql import Audit
        >>> bn = SQLAlchemyBackend()
        >>> session = bn.session()
        >>> audit = Audit('silo', 24, 'skimmed 100 tech', 'dj', '', 1359350165)
        >>> session.add(audit)
        >>> session.commit()
        >>> list(bn._conn.execute('select * from audit'))
        [(1, u'silo', 24, u'skimmed 100 tech', u'dj', u'', 1359350165)]
    """

    zope.interface.implements(ITrackerBackend)

    def __init__(self, src=None):
        if not src:
            src = 'sqlite://'

        self._conn = create_engine(src)
        self._metadata = MetaData()
        self._metadata.reflect(bind=self._conn)
        Base.metadata.create_all(self._conn)
        self._sessions = sessionmaker(
            bind=self._conn,
            expire_on_commit=False,
        )

        self._towers = {}

        self._addDefaultData()

    def _addDefaultData(self):
        session = self.session()
        session.merge(Category('tower', 'label', 'Label for the tower.'))
        session.merge(Category('tower', 'notice', 'A notice.'))
        session.merge(Category('fuel', 'fueled', 'A claim for fueling.'))
        session.merge(Category('silo', 'emptied', 'A claim for emptying'))
        session.commit()

    def session(self):
        return self._sessions()

    def currentApiUsage(self, completed=False):
        """
        Report the current Api usage.

        Returns a dictionary with tuple with statistics as follows:

        First value is the time when the last API call was made

        Second value is the time when the API concluded.  None if it was
        Not concluded

        Third value is the conclusion state.

        0
            Success
        1
            In progress
        2
            Failed with error
        """

        # query for stuff
        session = self.session()
        logs = session.query(ApiUsageLog)

        logs = logs.order_by(
            desc(ApiUsageLog.start_ts)).group_by(ApiUsageLog.api_key
                ).having(func.max(ApiUsageLog.start_ts))

        if completed:
            logs = logs.filter(ApiUsageLog.end_ts != None)

        results = {}
        for log in logs:
            results[log.api_key] = (log.start_ts, log.end_ts, log.state)

        return results

    def completedApiUsage(self):
        return self.currentApiUsage(completed=True)

    def beginApiUsage(self, api_key, timestamp=None):
        """
        Return a marker for an API usage.

        returns a usage marker.
        """

        usage = ApiUsageLog(api_key, timestamp)
        session = self.session()
        session.add(usage)
        session.commit()
        session.expunge(usage)
        return usage

    def endApiUsage(self, usage, state, timestamp=None):
        """
        Ends api usage

        mark the usage marker as completed, with the state it is at.
        """

        if timestamp is None:
            timestamp = int(time.time())
        usage.state = state
        usage.end_ts = timestamp
        session = self.session()
        session.merge(usage)
        session.commit()

    def reinstantiate(self):
        """
        Recreate all the objects in the tracker from the database.
        """

        logger.info('Reinstantiation requested.')
        session = self.session()
        towerq = session.query(Tower)
        self._towers = {}

        towers = towerq.all()
        count = len(towers)

        logger.info('%d towers to reinstantiate.', count)

        for c, tower in enumerate(towers):
            logger.debug('(%d/%d) towers reinstantiated.', c, count)
            tower._initDerived()
            tower._reloadResources(session)
            self._towers[tower.id] = tower

        # detatch all objects loaded with this session.
        logger.info('(%d/%d) towers reinstantiated.', count, count)
        session.expunge_all()

    def _queryTower(self, session, itemID):
        # see if we already have this tower_id registered.
        q = session.query(Tower).filter(Tower.itemID == itemID)
        try:
            result = q.one()
        except NoResultFound:
            # normal.
            return None
        except MultipleResultsFound:
            # this is abnormal, something may have tempered with the
            # database.
            raise

        return result

    def addTower(self, itemID, *a, **kw):
        """
        Add a tower.

        Doesn't actually set a tower to some state, just append for now
        to log all changes made to a tower.
        """

        # A better plan may be this: have a table that maps internal ID
        # with the API one, and the timestamps and other related fields
        # be maintained separately from it.  For now this will do for a
        # basic demo of just the fuel tracking.

        session = self.session()

        if itemID:
            # XXX the check should include rest of the fields.
            result = self._queryTower(session, itemID)
            if result:
                return self._towers[result.id]

        tower = Tower(itemID, *a, **kw)
        session.add(tower)
        session.commit()

        self._towers[tower.id] = tower
        session.expunge(tower)

        return tower

    def getFuelLog(self, tower_id):
        """
        Return the fuel logs for tower_id
        """

        session = self.session()
        q = session.query(Fuel).filter(Fuel.tower_id == tower_id).order_by(
            desc(Fuel.timestamp))
        result = q.all()
        session.expunge_all()
        return result

    def getTower(self, tower_id, default=_marker):
        """
        Return a copy of the tower at its current state.
        """

        # XXX not actually a copy yet.
        if default is not _marker:
            return self._towers.get(tower_id, default)
        return self._towers[tower_id]

    def getTowerIds(self):
        return self._towers.keys()

    def getTowerLog(self, tower_id):
        """
        Return the tower logs for tower_id
        """

        session = self.session()
        q = session.query(TowerLog).filter(TowerLog.tower_id == tower_id
            ).order_by(desc(TowerLog.timestamp))
        result = q.all()
        session.expunge_all()
        return result

    def updateTower(self, tower):
        """
        Update this tower.

        Returns True if updated, False otherwise.
        """

        # TODO proper error/exception handling.
        session = self.session()

        session.add(tower)

        tower_attrs = [getattr(tower, c) for c in tower.__table__.c.keys()]
        tower_log = TowerLog(*tower_attrs)
        session.add(tower_log)

        session.commit()
        session.expunge(tower)

        return True

    def addFuel(self, tower=None, fuelTypeID=None, delta=None, timestamp=None,
            value=None, *a, **kw):

        tower_id = tower.id
        fuel = Fuel(tower_id, fuelTypeID, delta, timestamp, value)

        session = self.session()
        session.add(fuel)
        session.commit()

        return fuel

    def setTowerApi(self, tower_id, api_key, currentTime):
        """
        Sets the tower API.
        """

        # don't trigger autoincrement.
        assert tower_id is not None

        tower_api = TowerApi(tower_id, api_key, currentTime)
        session = self.session()
        session.merge(tower_api)
        session.commit()

    def getTowerApis(self, api_key=None):
        # TODO implement filters.
        session = self.session()
        q = session.query(TowerApi)
        result = q.all()
        session.expunge_all()
        return result

    def addAudit(self, obj, reason, category, user, timestamp=None):
        """
        Add an audit entry for the object.
        """

        table = obj.__table__.name
        rowid = obj.id

        audit = Audit(table, rowid, reason, category, user, timestamp)

        session = self.session()
        session.add(audit)
        session.commit()

    def getApiKeys(self):
        """
        Return all the API keys.
        """

        session = self.session()
        q = session.query(APIKey)
        result = q.all()
        session.expunge_all()
        return result


class SQLAPIKeyManager(object):

    zope.interface.implements(IAPIKeyManager)

    def __init__(self, backend):
        self.backend = backend

    def getAllWith(self, cls):
        api_keys = self.backend.getApiKeys()
        return [cls(api=evelink.API(api_key=(api_key.key, api_key.vcode)))
            for api_key in api_keys]

