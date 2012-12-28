EVE POS Tracker
===============

This POS tracker aims to bring comprehensive coverage for management of
tasks commonly done by the logistics team of sovereignty holding
coalitions or alliances in the MMORPG EVE Online.  These tasks include
the management of player owned structures (POS, also known as control
towers), resource caches and distribution of workload amongst the
logistics team.

Management of player owned structures involves knowing where they are,
what function(s) they may serve, who should attend or has been attending
them and lastly, how much fuel remains or resources have accumulated in
them.  This task is aided by knowing how much fuel are available to keep
the operations running, and naturally note down which team members may
be available for any tasks at hand.

Demonstration
=============

The following is a demonstration of the functions provided by this pos
tracker module, an overview from the foundations to the overall
management classes.

To begin, install the dummy data helper class::

    >>> from mtj.eve.tracker.tests import dummyevelink
    >>> import mtj.eve.tracker.pos
    >>> dummyevelink.installDummy(mtj.eve.tracker.pos)

Tower Basics
------------

At the core for every pos tracker are the classes for the tracking of
the actual control towers.  The following is a brief introduction on the
tower classes to show how the pos tracker is constructed at the core.

Tower initialization
~~~~~~~~~~~~~~~~~~~~

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

    >>> tower2 = Tower(1000002, 16214, 30004268, 40270415, 4,
    ...     1325376000, 1306887061, 498125261)
    >>> tower2.initFuels()
    >>> sorted(tower2.fuels.keys())
    [4246, 16275, 24592]
    >>> tower2.celestialName
    u'Shenda VIII - Moon 8'

Low security, on the other hand, shouldn't need a charter either::

    >>> tower3 = Tower(1000003, 16214, 30004267, 40270327, 4,
    ...     1325376000, 1306886400, 1018389948)
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
    >>> sorted(tower1.verifyResources(fuel1, 1325376000))
    [4247, 16275]

The return values are the fuel types that does not match the expected
value given the input.  This means the fuel levels will need to be
updated, like so::

    >>> tower1.updateResources(fuel1, 1325376000)

Apply the fuel update to the highsec tower also.  Note that fuel types
not previously initialized will not be added::

    >>> fuel2 = {
    ...     4247: 12345,
    ...     4246: 19999,
    ...     16275: 7200,
    ...     24592: 200,
    ... }
    >>> tower2.updateResources(fuel2, 1325376000)
    >>> sorted(tower2.fuels.keys())
    [4246, 16275, 24592]

Day-to-day fuel calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Back to the first tower.  As its owner's alliance has sovereignty in the
system, the fuel consumption rate should reflect the discounts granted::

    >>> tower1.fuels[4247].delta
    30
    >>> tower1.fuels[16275].delta
    300

Second tower is in highsec, so no discounts and the need for charters::

    >>> tower2.fuels[4246].delta
    40
    >>> tower2.fuels[16275].delta
    400
    >>> tower2.fuels[24592].delta
    1

Now let's see if we can get the fuel levels ten hours after the initial
setup::

    >>> sorted(tower1.getResources(timestamp=1325412000).items())
    [(4247, 12045), (16275, 7200)]

For the second tower, we use the same timestamp, ten hours after the
fuel level check::

    >>> sorted(tower2.getResources(timestamp=1325412000).items())
    [(4246, 19599), (16275, 7200), (24592, 190)]

However, if we elapse the time by another thirty minutes, a different
story emerges.  Since the second tower ticks on the 11m01s mark, the
previous update was already 48m59s out of date, so there is really in
fact eleven cycles worth of fuel consumed at this point for the second
tower::

    >>> sorted(tower1.getResources(timestamp=1325413800).items())
    [(4247, 12045), (16275, 7200)]
    >>> sorted(tower2.getResources(timestamp=1325413800).items())
    [(4246, 19559), (16275, 7200), (24592, 189)]

Fuel consumption needs to be linked, as the moment when one fuel type
is depleted the tower will no longer be online, so any excess fuels of
other types will not be consumed::

    >>> sorted(tower2.getResources(timestamp=1326092400).items())
    [(4246, 12039), (16275, 7200), (24592, 1)]
    >>> sorted(tower2.getResources(timestamp=1326096000).items())
    [(4246, 11999), (16275, 7200), (24592, 0)]
    >>> sorted(tower2.getResources(timestamp=1326099600).items())
    [(4246, 11999), (16275, 7200), (24592, 0)]
    >>> sorted(tower2.getResources(timestamp=1326103200).items())
    [(4246, 11999), (16275, 7200), (24592, 0)]

Naturally there needs to be a way to know how long the POS will stay
online till::

    >>> tower1.getTimeRemaining(timestamp=1326855600)
    3600
    >>> tower1.getTimeRemaining(timestamp=1326859200)
    0
    >>> tower2.getTimeRemaining(timestamp=1326092400)
    4261
    >>> tower2.getTimeRemaining(timestamp=1326096000)
    661
    >>> tower2.getTimeRemaining(timestamp=1326099600)
    0

Tower Ownership and Sovereignty
-------------------------------

Due to wars, diplomacy and/or other circumstances, sovereignty status of
the system any given tower against its ownership may change, granting or
removing fuel discounts.  This need to be tracked to ensure accurate
bookkeeping of fuel levels.

To simulate sovereignty changes, we can forcibily set our dummy api
wrapper to provide the desired values::

    >>> tower1.findSovStatus()
    True
    >>> mtj.eve.tracker.pos.evelink_helper.sov_index = 1
    >>> tower1.findSovStatus()
    False

Now the owner of tower1 no longer gain sovereignty bonuses as the
ownership state is reverted to unclaimed.  Provide the timestamp for
when this happened and update the owner details like so::

    >>> tower1.getTimeRemaining(timestamp=1326000000)
    859200
    >>> tower1.updateSovOwner(timestamp=1326000000)
    >>> tower1.getTimeRemaining(timestamp=1326000000)
    643200
    >>> tower1.getResources(timestamp=1326000000)[4247]
    7155

Consumption should continue at the normal non-discounted rate::

    >>> tower1.getResources(timestamp=1326002400)[4247]
    7115
    >>> tower1.getResources(timestamp=1326639600)[4247]
    35
    >>> tower1.getTimeRemaining(timestamp=1326640000)
    3200

After some time someone remembers to pay the sovereignty bill (or fix
the TCU or whatever) and brought the sovereignty status back up just in
time, buying an extra hour for the tower::

    >>> mtj.eve.tracker.pos.evelink_helper.sov_index = 0
    >>> tower1.findSovStatus()
    True
    >>> tower1.updateSovOwner(timestamp=1326640000)
    >>> tower1.getTimeRemaining(timestamp=1326640000)
    6800
