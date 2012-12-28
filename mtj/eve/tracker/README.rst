EVE POS Tracker
===============

The following is a brief introduction on the basic initialization and
demonstration the pos tracker in action.

First we instantiate the dummy data helper class::

    >>> from mtj.eve.tracker.tests import dummyevelink
    >>> import mtj.eve.tracker.pos
    >>> dummyevelink.installDummy(mtj.eve.tracker.pos)

Tower initialization
--------------------

First initialize a tower.  This process will fetch the fuel requirements
from evedb and the API for the empire currently controlling the system
for the charter requirements::

    >>> from mtj.eve.tracker.pos import Tower
    >>> tower1 = Tower(1000001, 12235, 30004608, 40291202, 4,
    ...     1325376000, 1306886400, 498125261)
    >>> tower1.initFuels()
    >>> sorted(tower1.fuels.keys())
    [4247, 16275]
    >>> tower1.solarSystemName
    u'6VDT-H'
    >>> tower1.celestialName
    u'6VDT-H III - Moon 1'
    >>> tower1.allianceID
    498125261

As the above is a null security system, no charters are required.  We
can try again using one in high security space::

    >>> tower2 = Tower(1000001, 16214, 30004268, 40270415, 4,
    ...     1325376661, 1306887061, 498125261)
    >>> tower2.initFuels()
    >>> sorted(tower2.fuels.keys())
    [4246, 16275, 24592]
    >>> tower2.celestialName
    u'Shenda VIII - Moon 8'

Low security, on the other hand, shouldn't need a charter either::

    >>> tower3 = Tower(1000001, 16214, 30004267, 40270327, 4,
    ...     1325376661, 1306887061, 1018389948)
    >>> tower3.initFuels()
    >>> sorted(tower3.fuels.keys())
    [4246, 16275]
    >>> tower3.celestialName
    u'Nema X - Moon 10'
    >>> tower3.allianceID
    498125261

Adding/setting fuel levels
~~~~~~~~~~~~~~~~~~~~~~~~~~

The primary function of the pos tracker is to track fuel levels, and to
do that the current fuel levels must be added.  The values are generally
derived from the API, but they can be manually added.

To set fuel levels, first verify that the levels needs updating::

    >>> fuel1 = {
    ...     4247: 12345,
    ...     16275: 7200,
    ... }
    >>> sorted(tower1.verifyResources(fuel1, 1338508800))
    [4247, 16275]

The return values are the fuel types that does not match the expected
value given the input.  This means the fuel levels will need to be
updated, like so::

    >>> tower1.updateResources(fuel1, 1338508800)

Apply the fuel update to the highsec tower also::

    >>> fuel2 = {
    ...     4246: 19999,
    ...     16275: 7200,
    ...     24592: 200,
    ... }
    >>> tower2.updateResources(fuel2, 1338508800)

Day-to-day fuel calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Back to the first tower.  As its owner's alliance has sovereignty in the
system, the fuel consumption rate should reflect the discounts granted::

    >>> tower1.fuels[4247].delta
    30
    >>> tower1.fuels[16275].delta
    300
    >>> tower2.fuels[4246].delta
    40
    >>> tower2.fuels[16275].delta
    400
    >>> tower2.fuels[24592].delta
    1
