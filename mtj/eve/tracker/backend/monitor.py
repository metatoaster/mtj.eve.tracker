"""
This module provides decorator functions for methods within data classes
that monitors for updated attributes.
"""

import functools
import logging

import zope.component

from mtj.eve.tracker.interfaces import ITrackerBackend

logger = logging.getLogger('mtj.eve.tracker.backend.monitor')

def extract(inst, attributes):
    return [(a, getattr(inst, a, None)) for a in attributes]

def towerUpdates(*attributes):
    """
    Decorator for methods within the `Tower` class that monitors for
    changes within the provided attributes, and triggers the update
    method if appropriate.

    Arguments are the name of the attributes to monitor for.
    """

    def decorator(f):

        @functools.wraps(f)
        def wrapper(inst, *a, **kw):
            # XXX consider acquring the tracker (transaction) here so
            # that nested calls will result in an empty transaction
            # object.   Rather, a deferred call.
            before = extract(inst, attributes)
            result = f(inst, *a, **kw)

            tracker = zope.component.queryUtility(ITrackerBackend)
            if tracker is None:
                logger.warning('unable to acquire `ITrackerBackend` utility '
                    'for tower update.')
                return result

            after = extract(inst, attributes)

            if before != after:
                # XXX need to check that the tracker actually supports
                # this tower instance.
                tracker.updateTower(inst)

            return result

        return wrapper

    return decorator

def towerResourceBuffer(f):
    """
    Decorator for Tower.setResourceBuffer.

    Reasoning to move that here is to keep the backend interaction to
    this one module.
    """

    @functools.wraps(f)
    def wrapper(inst, *a, **kw):
        result = f(inst, *a, **kw)

        tracker = zope.component.queryUtility(ITrackerBackend)
        if tracker is None:
            # Assume this is running in standalone mode.
            logger.warning('unable to acquire `ITrackerBackend` utility '
                'for tower update.')
            return

        # XXX need to check that the tracker actually supports this
        # tower instance.
        tracker.addFuel(**result)

    return wrapper
