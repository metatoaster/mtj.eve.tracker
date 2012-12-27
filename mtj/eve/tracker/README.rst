EVE POS Tracker
===============

The following is a brief introduction on the basic initialization and
demonstration the pos tracker in action.

Right now we don't have mocks, so set up a cache to limit hits::

    >>> import tempfile
    >>> import os.path
    >>> from mtj.eve.tracker import cache
    >>> cache_file = os.path.join(tempfile.gettempdir(), 'evelink_mjt.sqlite')
    >>> cache.set_evelink_cache(cache_file)

Tower initialization
--------------------

First initialize a tower.  This process will fetch the fuel requirements
from evedb and the API for the empire currently controlling the system
for the charter requirements::

    >>> from mtj.eve.tracker.pos import Tower
    >>> tower1 = Tower(1000001, 12235, 30004608, 40291202, 4,
    ...     1325376000, 1306886400, 498125261)
    >>> tower1.initFuels()
    >>> len(tower1.fuels)
    2

As the above is a null security system, no charters are required.  We
can try again using one in high security space::

    >>> from mtj.eve.tracker.pos import Tower
    >>> tower2 = Tower(1000001, 12235, 30004268, 40270415, 4,
    ...     1325376000, 1306886400, 498125261)
    >>> tower2.initFuels()
    >>> len(tower2.fuels)
    3

Adding/setting fuel levels
~~~~~~~~~~~~~~~~~~~~~~~~~~

The primary function of the pos tracker is to track fuel levels, and to
do that the current fuel levels must be added.  The values are generally
derived from the API, but they can be manually added.

To set fuel levels, first verify that the levels needs updating::

    >>> fuels = {
    ...     4247: 12345,
    ...     16275: 7200,
    ... }
    >>> sorted(tower1.verifyResources(fuels, 1338508800))
    [4247, 16275]

The return values are the fuel types that does not match the expected
value given the input.  This means the fuel levels will need to be
updated, like so::

    >>> fuels = {
    ...     4247: 12345,
    ...     16275: 7200,
    ... }
    >>> sorted(tower1.verifyResources(fuels, 1338508800))
    [4247, 16275]

Day-to-day fuel calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Back to the first tower.  As its owner's alliance has sovereignty in the
system, the fuel consumption rate should reflect the discounts granted::
