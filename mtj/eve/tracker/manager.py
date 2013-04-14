from __future__ import absolute_import

import time
import logging

from evelink.api import APIError

import zope.component
import zope.interface

from mtj.eve.tracker.interfaces import ITrackerBackend, ITowerManager
from mtj.eve.tracker.interfaces import IAPIKeyManager
from mtj.eve.tracker import evelink

logger = logging.getLogger('mtj.eve.pos.manager')


class APIKeyManager(object):
    """
    Base class for managing API keys.
    """

    zope.interface.implements(IAPIKeyManager)

    def __init__(self, api_keys=None):
        if api_keys is None:
            api_keys = {}
        assert isinstance(api_keys, dict)

        self.api_keys = api_keys

    def getAllWith(self, cls):
        return [cls(api=evelink.API(api_key=(id_, vcode))) for id_, vcode in
            self.api_keys.iteritems()]


class BaseTowerManager(object):
    """
    A class that gathers the loose bits of functions.
    """

    zope.interface.implements(ITowerManager)

    def __init__(self, backend):
        self._setBackend(backend)
        # TODO setup evelink cache here too?

    def _setBackend(self, backend):
        if not ITrackerBackend.providedBy(backend):
            raise TypeError('provided backend is not of the correct type')
        self.backend = backend

    def importWithCorp(self, corp):
        """
        Takes a fully prepared evelink corp API object (cache + keys) to
        instantiate towers.

        corp
            - the corp API object.
        """

        starbases = corp.starbases()
        starbases_c = len(starbases)

        logger.info('%d starbases returned', starbases_c)

        for c, item in enumerate(starbases.iteritems()):
            k, v = item
            logger.info('(%d/%d) starbases processed.', c, starbases_c)
            logger.info('processing itemID: %s', k)
            tower = self.backend.addTower(**v)

            # Get time right before the request.
            try:
                ts = time.time()
                details = corp.starbase_details(k)
            except APIError as e:
                logger.warning('Fail to retrieve corp/StarbaseDetail for %s; '
                    'corp/StarbaseList may be out of date', k)
                continue

            # Determine relevant fields.
            api_time = corp.api.last_timestamps['current_time']
            state_ts = details['state_ts'] or 0
            delta = api_time - state_ts
            state = details['state']

            logger.info('timestamps (%s, %s, %s) | delta %d',
                ts, api_time, state_ts, delta)

            # supply the new stateTimestamp.
            tower.updateResources(details['fuel'], api_time,
                stateTimestamp=state_ts, omit_missing=False)

            # This is done after the resources to not interfere with the
            # resource verification.
            tower.setState(state)

            # Finally log down this tower as having updated with api.
            # Reason why we don't use the tower's api itemID is because
            # we could be tracking the previous locations of the same
            # tower that may have been anchored elsewhere, as a tower's
            # itemID is not reset when unanchored.  This is why some
            # corporation ensure that every unanchored tower is to be
            # repackaged before being anchored again, if possible.
            self.backend.setTowerApi(tower.id, corp.api.api_key[0], api_time)

        logger.info('(%d/%d) processing complete', starbases_c, starbases_c)


class DefaultTowerManager(BaseTowerManager):
    """
    Default tower manager that acquires whatever default backend that is
    currently registered if one is not provided.
    """

    def __init__(self, backend=None):
        if not backend:
            self.backend = zope.component.queryUtility(ITrackerBackend)
            if not ITrackerBackend.providedBy(self.backend):
                raise TypeError('No appropriate backend is registered.')
        else:
            self._setBackend(backend)


class TowerManager(BaseTowerManager):
    """
    The main tower manager.

    Requires explicit backend, and provides
    """

    def __init__(self, backend=None):
        if not ITrackerBackend.providedBy(backend):
            raise TypeError('inappropriate backend is provided.')

        self._setBackend(backend)
        self._api_keys = {}

    def addApiKey(self, api_id, vcode):
        self._api_keys[api_id] = vcode

    def importAll(self):
        keyman = zope.component.queryAdapter(self.backend, IAPIKeyManager)

        if keyman is None:
            keyman = zope.component.queryUtility(IAPIKeyManager)

        if not keyman:
            logger.warning('No key manager is present')
            return

        corps = keyman.getAllWith(evelink.Corp)
        for corp in corps:
            error = 0
            m_usage = self.backend.beginApiUsage(corp.api.api_key[0])
            try:
                self.importWithCorp(corp)
            except:
                # well crap.
                logger.exception('Import failed with uncatched exception')
                error = 1
            self.backend.endApiUsage(m_usage, error)
