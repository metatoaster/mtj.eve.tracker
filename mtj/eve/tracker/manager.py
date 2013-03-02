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

    def __init__(self):
        self.backend = zope.component.queryUtility(ITrackerBackend)
        if not ITrackerBackend.providedBy(self.backend):
            raise TypeError('No appropriate backend is registered')

        # XXX set up evelink cache
        self.logger = logger

    def importWithApi(self, api):
        """
        Takes a fully prepared evelink API object (cache + keys) to
        instantiate towers.
        """

        corp = evelink.Corp(api)
        starbases = corp.starbases()
        starbases_c = len(starbases)
        logger.debug('%d starbases returned', starbases_c)

        for c, item in enumerate(starbases.iteritems()):
            k, v = item
            logger.debug('(%d/%d) starbases processed.', c, starbases_c)
            logger.debug('processing itemID: %d', k)
            tower = self.backend.addTower(**v)

            # Get time right before the request.
            ts = time.time()
            details = corp.starbase_details(k)
            api_time = api.last_timestamps[0]
            state_ts = details['state_ts'] or 0
            delta = api_time - state_ts
            logger.debug('timestamps (%s, %s, %s) | delta %d',
                ts, api_time, state_ts, delta)

            state = details['state']
            tower.updateResources(details['fuel'], api_time)

        logger.debug('(%d/%d) processing complete', starbases_c, starbases_c)
