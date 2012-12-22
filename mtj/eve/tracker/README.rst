EVE POS Tracker
===============

The following is a brief introduction on the basic initialization and
demonstration the pos tracker in action.

First initialize a tower::

    >>> from mtj.eve.tracker.pos import Tower
    >>> tower = Tower('6VDT-H', 5, 2, 'online')
    >>> sorted(tower.resources.keys())
    ['Amarr Fuel Block', 'Charter', 'Strontium']
