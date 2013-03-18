import time
import logging

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

        logger.debug('%d starbases returned', starbases_c)

        for c, item in enumerate(starbases.iteritems()):
            k, v = item
            logger.debug('(%d/%d) starbases processed.', c, starbases_c)
            logger.debug('processing itemID: %s', k)
            tower = self.backend.addTower(**v)

            # Get time right before the request.
            ts = time.time()
            details = corp.starbase_details(k)
            api_time = corp.api.last_timestamps[0]
            state_ts = details['state_ts'] or 0
            delta = api_time - state_ts
            logger.debug('timestamps (%s, %s, %s) | delta %d',
                ts, api_time, state_ts, delta)

            state = details['state']
            # future state_ts is accurate accounted for.
            # state_ts in the past may mean the pos isn't "processed",
            # but fuel reported is still correct to the time polled 
            # regardless of that.
            tower.updateResources(details['fuel'], max(state_ts, api_time))

        logger.debug('(%d/%d) processing complete', starbases_c, starbases_c)


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
