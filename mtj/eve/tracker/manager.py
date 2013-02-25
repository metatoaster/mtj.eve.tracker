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
            # XXX details can be cached, and so ts should really be the
            # timestamp for when the original request was made
            # XXX pending on adding this function to the evelink fork.

            # XXX I have significant uncertainty on the timestamp, as it
            # may be fast?

            state = details['state']
            if state == 'online':
                # only online timestamp is sort of trustworthy, even
                # though it might be some time in the future.
                timestamp = details['state_ts']
                delta = ts - timestamp
                logger.debug('ts [%d] - state_ts [%d] = delta [%d]',
                    ts, timestamp, delta)
                if delta < 0:
                    # CCP doesn't return the future calculated values
                    # correctly, it actually reports what it was exactly
                    # an hour ago.
                    timestamp = timestamp - 3600
                    logger.debug('negative delta, assume :ccp:, timestamp is:',
                        timestamp)
            else:
                timestamp = ts
                logger.debug('not online, using current time [%d]', ts)

            tower.updateResources(details['fuel'], timestamp)

        logger.debug('(%d/%d) processing complete', starbases_c, starbases_c)
