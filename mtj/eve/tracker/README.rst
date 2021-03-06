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


Backend
-------

Ensure that we have a valid backend available for usage.  This can be
acquired using the Zope component framework like so::

    >>> import zope.component
    >>> from mtj.eve.tracker.interfaces import IAPIHelper, ITrackerBackend
    >>> backend = zope.component.queryUtility(ITrackerBackend)
    >>> ITrackerBackend.providedBy(backend)
    True

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

    >>> tower1 = backend.addTower(1, 12235, 30004608, 40291202, 4,
    ...     1325376000, 1306886400, 498125261)
    >>> sorted(tower1.updateResources({}, 1325376000))
    [4247, 16275]
    >>> sorted(tower1.fuels.keys())
    [4247, 16275]
    >>> tower1.solarSystemName
    u'6VDT-H'
    >>> tower1.regionName
    u'Fountain'
    >>> tower1.celestialName
    u'6VDT-H III - Moon 1'
    >>> tower1.allianceID
    498125261

As the above is a null security system, no charters are required.  We
can try again using one in high security space::

    >>> tower2 = backend.addTower(2, 20066, 30004268, 40270415, 4,
    ...     1325376661, 1306886400, 498125261)
    >>> sorted(tower2.updateResources({}, 1325376000))
    [4246, 16275, 24592]
    >>> tower2.celestialName
    u'Shenda VIII - Moon 8'

Low security, on the other hand, shouldn't need a charter either::

    >>> tower3 = backend.addTower(3, 16214, 30004267, 40270327, 4,
    ...     1325376000, 1306886400, 1018389948)
    >>> sorted(tower3.updateResources({}, 1325376000))
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

    >>> sorted(tower1.updateResources(fuel1, 1325376000))
    [4247, 16275]

One other thing to note is that the timestamps are assumed to follow the
quirks of the API, which is the values returned are valid until the
stateTimestamp, except for the case where the stateTimestamp is in the
past, where the resource values are valid for now.  This necessitate
adjustments and the interal timestamp calculations are assisted using the
resourcePulseTimestamp method.  As the provided timestamp for the above
updateResource call divides into the stateTimestamp, it should have no
issues::

    >>> tower1.resourcePulseTimestamp(1325376000)
    1325376000

Apply the fuel update to the highsec tower also.  Note that fuel types
not previously initialized will not be added::

    >>> fuel2 = {
    ...     4247: 12345,
    ...     4246: 6543,
    ...     16275: 3600,
    ...     24592: 200,
    ... }
    >>> sorted(tower2.updateResources(fuel2, 1325376000))
    [4246, 16275, 24592]
    >>> sorted(tower2.fuels.keys())
    [4246, 16275, 24592]

However, this timestamp is assumed to bump to right before the expected
stateTimestamp::

    >>> tower2.resourcePulseTimestamp(1325376000)
    1325376661

Day-to-day fuel calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Back to the first tower.  As its owner's alliance has sovereignty in the
system, the fuel consumption rate should reflect the discounts granted::

    >>> tower1.fuels[4247].delta
    30
    >>> tower1.fuels[16275].delta
    300

Second tower is a small, and in highsec, so no sovereignty discounts and
the need for charters::

    >>> tower2.fuels[4246].delta
    10
    >>> tower2.fuels[16275].delta
    100
    >>> tower2.fuels[24592].delta
    1

Third tower is a large, and in lowsec, so no sovereignty discounts but
no need for charters::

    >>> tower3.fuels[4246].delta
    40
    >>> tower3.fuels[16275].delta
    400
    >>> tower3.fuels.get(24592) is None
    True

Fuel is immediately deducted after the valid period, i.e. the
stateTimestamp that was used to set the fuel level::

    >>> sorted(tower1.getResources(timestamp=1325376001).items())
    [(4247, 12315), (16275, 7200)]

Now let's see if we can get the fuel levels ten hours after the initial
setup::

    >>> sorted(tower1.getResources(timestamp=1325412000).items())
    [(4247, 12045), (16275, 7200)]

Try out the same on the second tower, and see that the stateTimestamp
also result in the expected outcome::

    >>> sorted(tower2.getResources(timestamp=1325376662).items())
    [(4246, 6533), (16275, 3600), (24592, 199)]

For the second tower, we use the same timestamp, ten hours after the
fuel level check.  The tower would also be on the tenth cycle::

    >>> sorted(tower2.getResources(timestamp=1325412000).items())
    [(4246, 6443), (16275, 3600), (24592, 190)]

Naturally, if we elapse the time by another one second, the first tower
will immediately consume the fuel for the eleventh cycle as demonstrated
before, with the second tower maintaining the same fuel levels.::

    >>> sorted(tower1.getResources(timestamp=1325412001).items())
    [(4247, 12015), (16275, 7200)]
    >>> sorted(tower2.getResources(timestamp=1325412001).items())
    [(4246, 6443), (16275, 3600), (24592, 190)]

Fuel consumption needs to be linked, as the moment when one fuel type
is depleted the tower will no longer be online, so any excess fuels of
other types will not be consumed::

    >>> sorted(tower2.getResources(timestamp=1326092400).items())
    [(4246, 4553), (16275, 3600), (24592, 1)]
    >>> sorted(tower2.getResources(timestamp=1326096000).items())
    [(4246, 4543), (16275, 3600), (24592, 0)]
    >>> sorted(tower2.getResources(timestamp=1326099600).items())
    [(4246, 4543), (16275, 3600), (24592, 0)]
    >>> sorted(tower2.getResources(timestamp=1326103200).items())
    [(4246, 4543), (16275, 3600), (24592, 0)]

Naturally there needs to be a way to know how long the POS will stay
online till::

    >>> tower1.getTimeRemaining(timestamp=1326852000)
    3600
    >>> tower1.getTimeRemaining(timestamp=1326855600)
    0
    >>> tower2.getTimeRemaining(timestamp=1326092400)
    4261
    >>> tower2.getTimeRemaining(timestamp=1326096000)
    661
    >>> tower2.getTimeRemaining(timestamp=1326099600)
    0

There is also a getState method that will derive the expected current
state from the fuel levels::

    >>> tower1.getState(timestamp=1326852000)
    4
    >>> tower1.getState(timestamp=1326855600)
    4
    >>> tower1.getState(timestamp=1326855601)
    1
    >>> tower2.getState(timestamp=1326096000)
    4
    >>> tower2.getState(timestamp=1326099600)
    1


Optimizing fuel levels
~~~~~~~~~~~~~~~~~~~~~~

While the Crucible expansion eliminated the need to balance individual
fuel components due to the introduction of fuel blocks, towers anchored
in empire space still need the charters and they can affect the optimum
fuel levels slightly.  Notwithstanding that, logistic pilots will need
to know what and how much fuel to bring to fully top up the tower in the
most optimize manner.

This method will return the ideal fueling ratios.  Note that sovereignty
consumption discounts are applied here also::

    >>> tower1.getIdealFuelRatio()
    {4247: 27990}
    >>> sorted(tower2.getIdealFuelRatio().items())
    [(4246, 6980), (24592, 698)]
    >>> tower3.getIdealFuelRatio()
    {4246: 28000}

This other method will return the ideal fueling amounts at this
timestamp, taking account of existing fuels::

    >>> tower1.getIdealFuelingAmount(timestamp=1325412000)
    {4247: 15945}
    >>> sorted(tower2.getIdealFuelingAmount(timestamp=1326093061).items())
    [(4246, 2427), (24592, 697)]
    >>> sorted(tower2.getIdealFuelingAmount(timestamp=1326096661).items())
    [(4246, 2437), (24592, 698)]

Reinforcement fuel
~~~~~~~~~~~~~~~~~~

As Strontium Clathrates are used and calculated quite differently from
normal fuels, a separate method is provided for this.  The default
implementation will use the full secondary fuel bay::

    >>> tower1.getTargetStrontiumAmount()
    16500
    >>> tower2.getTargetStrontiumAmount()
    4100
    >>> tower3.getTargetStrontiumAmount()
    16400

The method also support an optional argument for target reinforcement
length::

    >>> tower1.getTargetStrontiumAmount(0)
    0
    >>> tower1.getTargetStrontiumAmount(40)
    12000
    >>> tower2.getTargetStrontiumAmount(20)
    2000
    >>> tower3.getTargetStrontiumAmount(40)
    16000

Lastly, a method is provided to show the changes that must be made to
the amount of Strontium in the secondary bay to achieve the desired
reinformcement length::

    >>> tower1.getTargetStrontiumDifference(40)
    4800
    >>> tower2.getTargetStrontiumDifference(20)
    -1600

Tower Ownership and Sovereignty
-------------------------------

Due to wars, diplomacy and/or other circumstances, sovereignty status of
the system any given tower against its ownership may change, granting or
removing fuel discounts.  This need to be tracked to ensure accurate
bookkeeping of fuel levels.

To simulate sovereignty changes, we can forcibily set our dummy api
wrapper to provide the desired values::

    >>> tower1.querySovStatus()
    True
    >>> evelink_helper = zope.component.getUtility(IAPIHelper)
    >>> evelink_helper.sov_index = 1
    >>> tower1.querySovStatus()
    False

Now the owner of tower1 no longer gain sovereignty bonuses as the
ownership state is reverted to unclaimed.  First verify the current
levels and what the levels would have been::

    >>> tower1.getTimeRemaining(timestamp=1326000000)
    855600
    >>> tower1.getReinforcementLength()
    86400
    >>> tower1.getResources(timestamp=1326000000)[4247]
    7125
    >>> tower1.getResources(timestamp=1326002401)[4247]
    7095

Now provide the timestamp for this event and update the owner details::

    >>> tower1.updateSovOwner(timestamp=1326000000)
    >>> tower1.getTimeRemaining(timestamp=1326000000)
    643200
    >>> tower1.getResources(timestamp=1326000000)[4247]
    7125
    >>> tower1.getReinforcementLength()
    64800

Consumption should continue at the normal non-discounted rate::

    >>> tower1.getResources(timestamp=1326002401)[4247]
    7085
    >>> tower1.getResources(timestamp=1326639600)[4247]
    45
    >>> tower1.getResources(timestamp=1326639601)[4247]
    5
    >>> tower1.getTimeRemaining(timestamp=1326639600)
    3600
    >>> tower1.getTimeRemaining(timestamp=1326639601)
    3599

After some time someone remembers to pay the sovereignty bill (or fix
the TCU or whatever) and brought the sovereignty status back up just in
time, buying an extra hour for the tower::

    >>> evelink_helper.sov_index = 0
    >>> tower1.querySovStatus()
    True
    >>> tower1.updateSovOwner(timestamp=1326640000)
    >>> tower1.getTimeRemaining(timestamp=1326640000)
    3200
    >>> tower1.getReinforcementLength()
    86400

Silos, moon mining and reactions
--------------------------------

The primary use cases for towers are the mining of moon materials and
running reactions.  These are done using moon-harvesting arrays or
inside reactor arrays, with the ingredients and produced materials
stored in the silos.

Silo material tracking
~~~~~~~~~~~~~~~~~~~~~~

The pos tracker tracks the entire set of materials in an abstract way -
As there is no direct API methods to figure out which silo is attached
to what tower, this process will need to be done manually if the API
tracking of resources is to be implemented.  At this stage, all input
will be done manually, and there will be one buffer per resource type
rather than per silo to ease management.

Add a silo to tower1, and while at it, refuel it to full first::

    >>> tower1.updateResources({4247: 28000}, 1326641400)
    [4247]
    >>> silo_t = tower1.addSiloBuffer(16649, delta=100,
    ...     value=0, full=75000, timestamp=1326641400)

It should be attached to the tower, and will have a few more fields
filled out::

    >>> tower1.silos.get(16649) == silo_t
    True
    >>> print silo_t.typeName
    Technetium

As time progresses the fuel depletes and silo accumulates with that
delicious, delicious Technetium, so check it out::

    >>> sorted(tower1.getSiloLevels(timestamp=1326643201).items())
    [(16649, 100)]
    >>> sorted(tower1.getResources(timestamp=1326643201).items())
    [(4247, 27970), (16275, 7200)]

Note how the silo tick time is assumed to be in sync with the pose fuel
cycle time.

Now run it to full and see that it won't overflow the allocated space::

    >>> sorted(tower1.getSiloLevels(timestamp=1329343201).items())
    [(16649, 75000)]
    >>> sorted(tower1.getResources(timestamp=1329343201).items())
    [(4247, 5470), (16275, 7200)]

As usual, the logistics director neglected to source the required fuel
blocks beforehand.  The grunts realized they probably should empty that
silo before losing too many products, so they go and do that::

    >>> s = tower1.updateSiloBuffer(16649, value=0, timestamp=1329343200)
    >>> sorted(tower1.getSiloLevels(timestamp=1329346800).items())
    [(16649, 100)]

However, directors being lazy with stocking fuels means they don't want
that tech moon anyway::

    >>> sorted(tower1.getSiloLevels(timestamp=1329994801).items())
    [(16649, 18100)]
    >>> sorted(tower1.getResources(timestamp=1329994801).items())
    [(4247, 40), (16275, 7200)]
    >>> tower1.getState(timestamp=1329994801)
    4
    >>> tower1.getOfflineTimestamp()
    1330002000

    >>> tower1.getState(timestamp=1329998401)
    4

    >>> sorted(tower1.getSiloLevels(timestamp=1330002001).items())
    [(16649, 18300)]
    >>> sorted(tower1.getResources(timestamp=1330002001).items())
    [(4247, 10), (16275, 7200)]
    >>> tower1.getState(timestamp=1330002001)
    1

Now that tower is no longer online.  Welp.  So because of that someone
went and took down that silo::

    >>> tower1.delSiloBuffer(16649)
    >>> sorted(tower1.getSiloLevels(timestamp=1330005601).items())
    []

Silo reactions
~~~~~~~~~~~~~~

For reactions, we will use another tower.  First fuel the silo to full
and add the buffers::

    >>> sorted(tower3.updateResources({4246: 28000, 16275: 4800}, 1326641400))
    [4246, 16275]
    >>> silo_p = tower3.addSiloBuffer(16644, products=(16662,), delta=100,
    ...     value=20000, full=20000, timestamp=1326641400)
    >>> silo_t = tower3.addSiloBuffer(16649, products=(16662,), delta=100,
    ...     value=20000, full=25000, timestamp=1326641400)
    >>> silo_pt = tower3.addSiloBuffer(16662, reactants=(16644, 16649,),
    ...     delta=200, value=0, full=40000, timestamp=1326641400)

Verify the initial levels::

    >>> sorted(tower3.getSiloLevels(timestamp=1326641400).items())
    [(16644, 20000), (16649, 20000), (16662, 0)]

Now run this for a while::

    >>> sorted(tower3.getSiloLevels(timestamp=1326645000).items())
    [(16644, 19900), (16649, 19900), (16662, 200)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327357800).items())
    [(16644, 100), (16649, 100), (16662, 39800)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327365000).items())
    [(16644, 0), (16649, 0), (16662, 40000)]

Now run this for a while::

    >>> sorted(tower3.getSiloLevels(timestamp=1326645000).items())
    [(16644, 19900), (16649, 19900), (16662, 200)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327357800).items())
    [(16644, 100), (16649, 100), (16662, 39800)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327365000).items())
    [(16644, 0), (16649, 0), (16662, 40000)]

Oops, it got full, better empty products and load in more reactants::

    >>> s = tower3.updateSiloBuffer(16644, value=20000, timestamp=1327365000)
    >>> s = tower3.updateSiloBuffer(16649, value=20000, timestamp=1327365000)
    >>> s = tower3.updateSiloBuffer(16662, value=0, timestamp=1327365000)

Dealing with reinforcement
--------------------------

With profits comes hostility.  There will be times when space nerds
bearing a different flag will come and shoot things up, putting a tower
into reinforcement.  This will stop them from attack, but also stops
tower modules from doing things like mining or reacting.

For this tracker, if a tower was reinforced, a method is provided to
mark this event.  This changes the stateTimestamp because reinforcement
mechanics seem to override everything::

    >>> tower3.getResources(timestamp=1327372200)[4246]
    19880
    >>> tower3.enterReinforcement(exitAt=1327501800, timestamp=1327372200)
    >>> tower3.getResources(timestamp=1327372200)[4246]
    19880
    >>> tower3.getResources(timestamp=1327501800)[4246]
    19880
    >>> tower3.stateTimestamp
    1327501800
    >>> tower3.getState(timestamp=1327372200)
    3

Fortunately, someone was out there to time the tower properly to 1d12h
(despite the initial lack of strontium).  The strontium bay should have
been properly deducted::

    >>> sorted(tower3.getResources(timestamp=1327372200).items())
    [(4246, 19880), (16275, 0)]

With the reaction completely stopped::

    >>> sorted(tower3.getSiloLevels(timestamp=1327372200).items())
    [(16644, 19800), (16649, 19800), (16662, 400)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327375800).items())
    [(16644, 19800), (16649, 19800), (16662, 400)]

Normal fuel consumption should also have stopped, even at the point of
time when the tower is supposed to exit reinforcement::

    >>> sorted(tower3.getResources(timestamp=1327501800).items())
    [(4246, 19880), (16275, 0)]

When the reinforcement cycle ends, tower is marked as online again::

    >>> tower3.getState(timestamp=1327501799)
    3
    >>> tower3.getState(timestamp=1327501800)
    4

Normal fuel consumption should resume::

    >>> sorted(tower3.getResources(timestamp=1327501801).items())
    [(4246, 19840), (16275, 0)]

However, the silos need to be manually marked as online again, to not
give the impression that things are mining when they are really not::

    >>> sorted(tower3.getSiloLevels(timestamp=1327501800).items())
    [(16644, 19800), (16649, 19800), (16662, 400)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327505400).items())
    [(16644, 19800), (16649, 19800), (16662, 400)]

Now someone with roles finally shows up to restront the tower and put
modules back online::

    >>> s = tower3.updateSiloBuffer(16644, online=True, timestamp=1327505400)
    >>> s = tower3.updateSiloBuffer(16649, online=True, timestamp=1327505400)
    >>> s = tower3.updateSiloBuffer(16662, online=True, timestamp=1327505400)

See that the values are accumulating as expected::

    >>> sorted(tower3.getSiloLevels(timestamp=1327509000).items())
    [(16644, 19700), (16649, 19700), (16662, 600)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327832999).items())
    [(16644, 10800), (16649, 10800), (16662, 18400)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327833000).items())
    [(16644, 10700), (16649, 10700), (16662, 18600)]

Oh yeah, should probably add strontium back into the bay::

    >>> tower3.exitReinforcement(strontium=14400, timestamp=1327372200)
    Traceback (most recent call last):
    ...
    ValueError: Cannot exit reinforcement 129600s before 1327501800

Too soon, I guess.  Wait a bit::

    >>> sorted(tower3.getResources(timestamp=1327869000).items())
    [(4246, 15800), (16275, 0)]
    >>> tower3.exitReinforcement(strontium=14400, timestamp=1327833600)
    >>> sorted(tower3.getResources(timestamp=1327869000).items())
    [(4246, 15800), (16275, 14400)]

Should not interfere with the silo calculations either::

    >>> sorted(tower3.getSiloLevels(timestamp=1327832999).items())
    [(16644, 10800), (16649, 10800), (16662, 18400)]
    >>> sorted(tower3.getSiloLevels(timestamp=1327833000).items())
    [(16644, 10700), (16649, 10700), (16662, 18600)]

Logging and replay
------------------

The logging mechanism is another key feature to this tracker.  All
manipulations to the buffers will be logged and can be used to audit
actions done to the pos network, and the entire set of events can be
replayed as desired.

Now let's see if we have the tower entries logged::

    >>> results = list(backend._conn.execute('select * from fuel'))
    >>> len(results)
    25
    >>> results[24]
    (25, 3, 16275, 400, 1327836600, 14400)
