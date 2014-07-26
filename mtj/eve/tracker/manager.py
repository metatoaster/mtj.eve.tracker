from __future__ import absolute_import

import time
import logging

from xml.etree import ElementTree
from evelink.api import APIError

import zope.component
import zope.interface

from mtj.eve.tracker.interfaces import ITrackerBackend, ITowerManager
from mtj.eve.tracker.interfaces import IAPIKeyManager
from mtj.eve.tracker import evelink

logger = logging.getLogger('mtj.eve.pos.manager')


@zope.interface.implementer(IAPIKeyManager)
class APIKeyManager(object):
    """
    Base class for managing API keys.
    """

    def __init__(self, api_keys=None):
        if api_keys is None:
            api_keys = {}
        assert isinstance(api_keys, dict)

        self.api_keys = api_keys

    def getAllWith(self, cls):
        return [cls(api=evelink.API(api_key=(id_, vcode))) for id_, vcode in
            self.api_keys.iteritems()]


@zope.interface.implementer(ITowerManager)
class BaseTowerManager(object):
    """
    A class that gathers the loose bits of functions.
    """

    def __init__(self):
        pass

    def importWithCorp(self, corp):
        """
        Takes a fully prepared evelink corp API object (cache + keys) to
        instantiate towers.

        corp
            - the corp API object.
        """

        backend = zope.component.queryUtility(ITrackerBackend)
        if not ITrackerBackend.providedBy(backend):
            logger.warning('No validtracker backend can be acquired, '
                           'nothing to do')
            return

        starbases = corp.starbases().result
        starbases_c = len(starbases)

        logger.info('%d starbases returned', starbases_c)

        for c, item in enumerate(starbases.iteritems()):
            k, v = item
            logger.info('(%d/%d) starbases processed.', c, starbases_c)
            logger.info('processing itemID: %s', k)

            try:
                tower = backend.addTower(**v)
            except TypeError:
                # can be caused by celestialId being undefined from an
                # unanchored tower.
                logger.warning('Fail to instantiate tower with the following '
                    'arguments as parameters: %s', v)
                continue

            logger.info('backend tower id: %s', tower.id)

            # Get time right before the request.
            try:
                ts = time.time()
                raw_details = corp.starbase_details(k)
            except APIError as e:
                logger.warning('Fail to retrieve corp/StarbaseDetail for %s; '
                    'corp/StarbaseList may be out of date', k)
                continue
            except ElementTree.ParseError as e:
                logger.warning('Fail to retrieve corp/StarbaseDetail for %s; '
                    'corp/StarbaseList response was invalid XML', k)
                continue

            # Determine relevant fields.
            api_time = raw_details.timestamp
            details = raw_details.result

            state_ts = details['state_ts'] or 0
            delta = api_time - state_ts
            state = details['state']

            logger.info('timestamps (%s, %s, %s) | delta %d',
                ts, api_time, state_ts, delta)

            # supply the new stateTimestamp and state.
            tower.setState(state=state, stateTimestamp=state_ts,
                timestamp=api_time,
                # Ensure the resources get updated at the same time.
                updateResources_kwargs={
                    'values': details['fuel'],
                    'timestamp': api_time,
                    'stateTimestamp': state_ts,
                    'omit_missing': False,
                })

            # Finally log down this tower as having updated with api.
            # Reason why we don't use the tower's api itemID is because
            # we could be tracking the previous locations of the same
            # tower that may have been anchored elsewhere, as a tower's
            # itemID is not reset when unanchored.  This is why some
            # corporation ensure that every unanchored tower is to be
            # repackaged before being anchored again, if possible.
            backend.setTowerApi(tower.id, corp.api.api_key[0], api_time)

        logger.info('(%d/%d) processing complete', starbases_c, starbases_c)


class TowerManager(BaseTowerManager):
    """
    The main tower manager.

    Requires explicit backend, and provides
    """

    def importAll(self):
        keyman = zope.component.queryUtility(IAPIKeyManager)
        backend = zope.component.queryUtility(ITrackerBackend)
        if not backend:
            logger.warning('No backend is present')
            return

        if not keyman:
            logger.warning('No key manager is present')
            return

        corps = keyman.getAllWith(evelink.Corp)
        for corp in corps:
            error = 0
            m_usage = backend.beginApiUsage(corp.api.api_key[0])
            try:
                self.importWithCorp(corp)
            except:
                # well crap.
                logger.exception('Import failed with uncaught exception')
                error = 1
            backend.endApiUsage(m_usage, error)

        # update the api key usage.
        backend.cacheApiTowerIds()

    def refresh(self):
        """
        Refresh all data from the db.
        """

        backend = zope.component.queryUtility(ITrackerBackend)
        if not backend:
            logger.warning('No backend is present')
            return

        return backend.reinstantiate()
