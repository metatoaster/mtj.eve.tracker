from __future__ import absolute_import

import time
import logging

from evelink.api import APIError

import zope.component

from mtj.eve.tracker.interfaces import ITrackerBackend
from mtj.eve.tracker import evelink

logger = logging.getLogger('mtj.eve.pos.manager')


class BaseTowerManager(object):
    """
    A class that gathers the loose bits of functions.
    """

    def __init__(self, backend):
        self._setBackend(backend)
        # TODO setup evelink cache here too?

    def _setBackend(self, backend):
        if not ITrackerBackend.providedBy(self.backend):
            raise TypeError('provided backend is not of the correct type')
        self.backend = backend

    def importWithApi(self, corp):
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

            api_time = corp.api.last_timestamps['current_time']
            state_ts = details['state_ts'] or 0
            delta = api_time - state_ts
            state = details['state']

            logger.info('timestamps (%s, %s, %s) | delta %d',
                ts, api_time, state_ts, delta)

            # supply the new stateTimestamp.
            tower.updateResources(details['fuel'], api_time,
                stateTimestamp=state_ts)

            # This is done after the resources to not interfere with the
            # resource verification.
            tower.setState(state)

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
