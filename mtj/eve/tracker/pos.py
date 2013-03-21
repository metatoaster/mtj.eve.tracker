import time
import sys

import zope.component

from mtj.evedb.structure import ControlTower
from mtj.evedb.map import Map
from mtj.evedb.market import Group

from mtj.multimer.buffer import TimedBuffer

from mtj.eve.tracker.backend import monitor
from mtj.eve.tracker.interfaces import IAPIHelper, ITrackerBackend

SECONDS_PER_HOUR = 3600
STRONTIUM_ITEMID = 16275
STATE_ANCHORED = 1
STATE_ONLINING = 2
STATE_REINFORCED = 3
STATE_ONLINE = 4

pos_info = ControlTower()
eve_map = Map()
item_info = Group()


class Tower(object):
    """
    A Player Owned Structure (POS).
    """
    # TODO verify the argument ordering of some methods in this class
    # that contain timestamp.  Value tends to be fuel value and they all
    # precede it, but other optional arguments have to follow after.

    def __init__(self, itemID, typeID, locationID, moonID, state,
            stateTimestamp, onlineTimestamp, standingOwnerID):
        """
        This should only be called once.

        The parameters are equivalent to /corp/StarbaseList.xml.
        """

        # the id is NOT set here as this attribute is backend dependent.

        # Hurr why can't this be done automagically from arguments...
        self.itemID = itemID
        self.typeID = typeID
        self.locationID = locationID
        self.moonID = moonID  # should validate against locationID

        # variable retrieved values
        self.state = state
        self.onlineTimestamp = onlineTimestamp
        self.standingOwnerID = standingOwnerID
        self.stateTimestamp = stateTimestamp

        self._initDerived()

    def _initDerived(self):
        # this can be None...
        self.resourcePulse = 0
        self.typeName = None
        self.allianceID = None
        self.celestialName = None
        self.solarSystemName = None
        self.capacity = None
        self.strontCapacity = None

        # variable derived values
        self.allianceID = None
        self.sov = None

        self._setDerivedValues()

        # The calculated values
        self.fuels = {}  # fuel
        self.silos = {}  # silos

    def _setDerivedValues(self):
        # TODO error checking and other validation somewhere
        self.setStateTimestamp(self.stateTimestamp)
        moon = eve_map.getCelestial(self.moonID)
        solar_system = eve_map.getSolarSystem(self.locationID)
        pos = pos_info.getControlTower(self.typeID)
        stront = pos_info.getControlTowerStrontCapacity(self.typeID)
        self.celestialName = moon['itemName']
        self.solarSystemName = solar_system['solarSystemName']
        self.typeName = pos['typeName']
        self.capacity = pos['capacity']
        self.strontCapacity = stront['capacitySecondary']

        # Not calling the update method defined below as this is part of
        # initialization.
        self.allianceID = self.queryAllianceID()
        self.sov = self.querySovStatus()

    @monitor.towerUpdates('stateTimestamp')
    def setStateTimestamp(self, stateTimestamp):
        """
        Method to update stateTimestamp.

        Users that need to update the stateTimestamp SHOULD use this
        method to ensure consistency as the management of resourcePulse
        time is also done here.

        Parameters:

        stateTimestamp
            the new stateTimestamp
        """

        if stateTimestamp is None:
            # This can happen when API says so when querying for a long
            # offline pos.  Just assume this to be 0.
            self.resourcePulse = 0
        else:
            self.resourcePulse = stateTimestamp % SECONDS_PER_HOUR

        self.stateTimestamp = stateTimestamp

    def queryAllianceID(self):
        """
        Return the alliance ID of the standing owner of this tower.
        """

        evelink_helper = zope.component.getUtility(IAPIHelper)
        if evelink_helper.alliances.get(self.standingOwnerID):
            return self.standingOwnerID
        else:
            return evelink_helper.corporations.get(self.standingOwnerID)

    def querySovStatus(self):
        # As the API does not provide the current development index
        # of the system, so if the discount is dependent on this
        # index, it will be impossible to reliably determine whether
        # the discount is indeed applied.
        evelink_helper = zope.component.getUtility(IAPIHelper)
        sov_info = evelink_helper.sov[self.locationID]
        return sov_info['alliance_id'] == self.allianceID

    def setResourceBuffer(self, bufferGroupName, bufferKey, delta, timestamp,
            purpose, value, resourceTypeName, unitVolume):
        """
        A unified method to assign buffers into the containers.

        bufferGroupName
            The name of the resource group to assign the buffer to.
        bufferKey
            The key used to identify this buffer within the bufferGroup.
        delta
            The delta value.
        timestamp
            The timestamp current to the value.
        purpose
            ID of the purpose of this buffer
        value
            The value for the amount of the tracked resource.
        resourceTypeName
            Human readable name of the resource type.
        unitVolume
            Volume of individual fuel units.
        """

        bufferGroup = getattr(self, bufferGroupName, None)

        # TODO this should be some sort of management smarter than a
        # simple dict.
        if not isinstance(bufferGroup, dict):
            raise ValueError('`%s` is not a valid bufferGroupName' %
                bufferGroupName)

        kargs = dict(delta=delta, timestamp=timestamp, purpose=purpose,
            value=value, resourceTypeName=resourceTypeName,
            unitVolume=unitVolume)
        res_buffer = TowerResourceBuffer(self, **kargs)
        bufferGroup[bufferKey] = res_buffer

        # XXX logging
        tracker = zope.component.queryUtility(ITrackerBackend)
        if tracker is None:
            # XXX handle error somehow?
            return

        # This need to be tracked.
        kargs['tower'] = self
        kargs['fuelTypeID'] = bufferKey
        tracker.addFuel(**kargs)

    def initResources(self):
        evelink_helper = zope.component.getUtility(IAPIHelper)
        all_fuels = pos_info.getControlTowerResource(self.typeID)
        sov_info = evelink_helper.sov[self.locationID]

        # Determine fuel type from systemID + factionID
        faction_id = sov_info['faction_id']
        security = eve_map.getSolarSystem(self.locationID)['security']

        for fuel in all_fuels:
            if fuel['factionID'] in (faction_id, None):
                if fuel['factionID'] and security < fuel['minSecurityLevel']:
                    # Lowsec don't need charters.
                    continue

                self.fuels[fuel['resourceTypeID']] = None

    def verifyResources(self, values, timestamp):
        """
        Verify resources with the given values

        values
            The values of the fuel levels.  Generally acquired from the
            API.
        timestamp
            The timestamp of the values.

        returns a list of fuel_id that mismatch from the input value.
        """

        mismatches = []
        if not self.fuels:
            self.initResources()

        for fuel_id, fuel_buffer in self.fuels.iteritems():
            if fuel_buffer is None:
                # initialized but no buffer, must be rectified.
                mismatches.append(fuel_id)
                continue

            verifier = values.get(fuel_id)
            if not verifier:
                # Can't verify against unspecified value.
                continue

            calculated = fuel_buffer.getCurrent(timestamp)
            if verifier != calculated.value:
                mismatches.append(fuel_id)

        return mismatches

    def updateResources(self, values, timestamp, stateTimestamp=None,
            force=False):
        """
        Updates resource levels.

        values
            The new values.  The value type should be a dict with the
            fuel id as key and value as the amount to be assigned.
        timestamp
            The timestamp that the values are current to.
        stateTimestamp
            If this is done via the API, pass in this too.  Since
            accurate time keeping can be difficult for CCP, there are
            magic involved when handling this argument, especially when
            the creators of this class think they (know how to) care
            about timing consistencies.
        force
            Optional argument.  If supplied, validation against existing
            levels are not done so an event will be forced.

        Possible return values
            List of typeIDs of resources updated.
        """

        def updateStateTimestamp(stateTimestamp):
            if stateTimestamp is None or not mismatches:
                # naturally, if fuel values are consistent just let any
                # possible difference slide.
                return

            state_ts_result = self.setStateTimestamp(stateTimestamp)

        # flag the need to update all the fuels.
        updateAll = not self.fuels
        mismatches = self.verifyResources(values, timestamp)

        update_values = {}
        if updateAll:
            # mismatches should be all the resources
            update_values = {v: 0 for v in mismatches}
        update_values.update(values)

        # dict comprehension
        all_fuels = {v['resourceTypeID']: v for v in
            pos_info.getControlTowerResource(self.typeID)}

        updateStateTimestamp(stateTimestamp)
        if stateTimestamp > timestamp:
            # assume all fuel values specified at future timestamps are
            # accurate (i.e. processed).
            timestamp = stateTimestamp

            # otherwise resourcePulseTimestamp will handle it.

        updated = []

        for resourceTypeID, value in update_values.iteritems():
            if resourceTypeID not in mismatches and not force:
                continue

            fuel = all_fuels.get(resourceTypeID)

            delta = fuel['quantity']
            if self.sov:
                delta = int(round(delta * 0.75))

            timestamp = self.resourcePulseTimestamp(timestamp)

            self.setResourceBuffer(
                bufferGroupName='fuels',
                bufferKey=resourceTypeID,
                delta=delta,
                timestamp=timestamp,
                purpose=fuel['purpose'],
                value=value,
                resourceTypeName=fuel['typeName'],
                unitVolume=fuel['volume'],
            )
            updated.append(resourceTypeID)

        return updated

    def updateSovOwner(self, timestamp, standingOwnerID=None):
        """
        Update the ownership of the tower.

        This will trigger an updateResource if the sov status changes
        """

        if standingOwnerID:
            self.standingOwnerID = standingOwnerID
        self.allianceID = self.queryAllianceID()
        sov = self.querySovStatus()

        if sov != self.sov:
            # Get the correct fuel values before sov status change.
            # XXX timestamp could be multiple things - it could be the
            # time when the corporation join/leaves the alliance, or the
            # timestamp of when the sovereignty status changed.  Trust
            # the provided value for now.
            values = self.getResources(timestamp)
            # Set the new sov value and then update
            self.sov = sov
            # force update
            self.updateResources(values, timestamp, force=True)

    def resourcePulseTimestamp(self, timestamp):
        """
        Calculate the buffer pulse with the given timestamp.

        This is to ensure resource buffer timestamps are set correctly
        so that the calculated values will be synchronized with actual
        values.
        """

        return ((timestamp - timestamp % SECONDS_PER_HOUR +
            int((timestamp % SECONDS_PER_HOUR) > self.resourcePulse) *
                SECONDS_PER_HOUR) + self.resourcePulse)

    def siloPulseTimestamp(self, timestamp):
        """
        Calculate the silo pulse with the given timestamp.

        This goes the opposite direction because the current assumption
        is that this is a secondary effect and API doesn't report the
        real values associated with this.  Yes it is a pure guess.
        """

        return ((timestamp - timestamp % SECONDS_PER_HOUR -
            int((timestamp % SECONDS_PER_HOUR) < self.resourcePulse) *
                SECONDS_PER_HOUR) + self.resourcePulse)

    def getResources(self, timestamp):
        """
        Get the current resource levels

        Return value:
            The new values.  The value type should be a dict with the
            fuel id as key and value as the amount to be assigned.
        """

        # everything after offline time will not be defined.
        timestamp = min(timestamp, self.getOfflineTimestamp())

        # dict comprehension
        return {key: fuel.getCurrent(timestamp=timestamp).value
            for key, fuel in self.fuels.iteritems()}

    def getIdealFuelRatio(self):
        """
        Get the ideal fuel ratio
        """

        # add all normal fuel volumes
        fuels = [f for k, f in self.fuels.iteritems() if f.isNormalFuel()]

        cycle_volume = 0
        for fuel in fuels:
            cycle_volume += fuel.unitVolume * fuel.delta

        ideal_cycles = int(self.capacity / cycle_volume)

        # dict comprehension
        return {k: f.delta * ideal_cycles for k, f in self.fuels.iteritems()
            if f.isNormalFuel()}

    def getTargetStrontiumCycles(self, target=None):
        fuel = self.fuels[STRONTIUM_ITEMID]
        if target is not None:
            return target
        return int(self.strontCapacity / (fuel.delta * fuel.unitVolume))

    def getTargetStrontiumAmount(self, target=None):
        """
        Get the target strontium amount as per desired reinforcement
        timing needs.
        """

        fuel = self.fuels[STRONTIUM_ITEMID]
        return fuel.delta * self.getTargetStrontiumCycles(target)

    def getTargetStrontiumDifference(self, target=None):
        """
        Return the difference needed to hit the target strontium amount.
        """

        fuel = self.fuels[STRONTIUM_ITEMID]
        return self.getTargetStrontiumAmount(target) - fuel.value

    def getIdealFuelingAmount(self, timestamp):
        """
        Get the optimum resource distribution.
        """

        current = self.getResources(timestamp)
        ratio = self.getIdealFuelRatio()

        # dict comprehension
        return {k: v - current.get(k) for k, v in ratio.iteritems()}

    def getOfflineTimestamp(self):
        """
        Figure out from all the fuels when will the pos go offline,
        which is the timestamp when no more fuel deduction can be made
        to any of the normal fuels.
        """

        offlineTimestamps = []
        for key, fuel in self.fuels.iteritems():
            if fuel is None or not fuel.isNormalFuel():
                continue

            offlineTimestamps.append(fuel.getCyclesPossible() * fuel.period 
                + fuel.expiry)

        if not offlineTimestamps:
            # Not sure if this is even the right result, it's undefined
            # but this only really happens if things are not initialized
            # correctly.  With a bunch of methods relying on this I am
            # going to return a number.
            return -1

        return min(offlineTimestamps)

    def getTimeRemaining(self, timestamp=None):
        """
        Get the time until the tower goes offline in seconds, at the
        specified timestamp.
        """

        if timestamp is None:
            timestamp = int(time.time())
        offlineAt = self.getOfflineTimestamp()
        return max(offlineAt - timestamp, 0)

    def getState(self, timestamp=None):
        """
        Derive the state at timestamp based on predefined rules and
        conditions.
        """

        if timestamp is None:
            timestamp = int(time.time())

        # Out of fuel special case
        if timestamp > self.getOfflineTimestamp():
            return STATE_ANCHORED

        # XXX verify that this will also apply for the onlining state.
        if self.state in [STATE_ONLINING, STATE_REINFORCED]:
            # Also assume the stateTimestamp is the moment it will be
            # online, not the last moment that it will be on the defined
            # state.
            if timestamp >= self.stateTimestamp:
                return STATE_ONLINE

        return self.state

    def getReinforcementLength(self):
        fuel = self.fuels.get(STRONTIUM_ITEMID)
        if not fuel:
            return 0
        remaining = fuel.getCyclesPossible() * fuel.period
        return remaining

    @monitor.towerUpdates('state')
    def enterReinforcement(self, exitAt, timestamp=None):
        """
        Helper method to trigger a reinforcement.  API update method can
        bypass this completely.
        """

        if timestamp is None:
            timestamp = int(time.time())

        resources = self.getResources(timestamp)
        resources[STRONTIUM_ITEMID] = 0

        # the exit stamp is the new stateTimestamp as per the API, and
        # so new pulse need to be calculated.
        self.setStateTimestamp(exitAt)

        self.updateResources(resources, exitAt, force=True)
        siloLevels = self.getSiloLevels(timestamp)
        for k, v in siloLevels.iteritems():
            self.updateSiloBuffer(k, value=v, timestamp=timestamp,
                online=False)

        # Finally set the state here, to not interfere with the above
        # calculations.
        self.state = STATE_REINFORCED

    @monitor.towerUpdates('state')
    def exitReinforcement(self, strontium, timestamp=None):
        """
        Used to verify reinforcement is completed, with new strontium
        added back into the strontium bay.
        """

        self.updateResources({STRONTIUM_ITEMID: strontium}, timestamp,
            force=True)
        self.state = STATE_ONLINE

    def attachSilo(self, itemID, typeID, resourceTypeID=None):
        """
        Attach a silo based directly on the API

        itemID
            the itemID of the server
        typeID
            the typeID of the silo
        resourceTypeID
            the typeID of the resource to track.
        """

        raise NotImplementedError()

    def delSiloBuffer(self, typeID):
        # XXX logging
        self.silos.pop(typeID, None)

    def setSiloBuffer(self, typeID, typeName, unitVolume, products, reactants,
            online, delta, value, full, timestamp=None):

        # TODO figure out how this actually accumulates.
        timestamp = self.siloPulseTimestamp(timestamp)
        silo = TowerSiloBuffer(self, typeName=typeName, unitVolume=unitVolume,
            products=products, reactants=reactants, online=online, delta=delta,
            value=value, full=full, timestamp=timestamp)
        self.silos[typeID] = silo
        # XXX logging

        # some values can be None, read directly from silo to reconfirm
        # for logging purposes

        timestamp = silo.timestamp
        return silo

    def addSiloBuffer(self, typeID, products=None, reactants=None, online=True,
            delta=1, value=0, full=100, timestamp=None, *a, **kw):
        """
        Adds a silo buffer, the abstract representation of a group of
        silos.  This also uses the item type specified
        the silo as a whole,

        typeID
            The typeID of the resource to track
        products
            If this resource leads into production of something, specify
            the list of typeID.
        reactants
            A list of reactants this resource needs.
        delta
            The absolute value of the rate of change for this resource.
        value
            The starting value.
        full
            The maximum value the buffer can represent.
        """

        if typeID in self.silos:
            raise ValueError('silo already tracking typeID')

        typeInfo = item_info.getType(typeID)
        if not typeInfo:
            raise ValueError('invalid typeID')

        typeName = typeInfo['typeName']
        unitVolume = typeInfo['volume']

        silo = self.setSiloBuffer(typeID, typeName=typeName,
            unitVolume=unitVolume, products=products, reactants=reactants,
            online=online, delta=delta, value=value, full=full,
            timestamp=timestamp)
        return silo

    def updateSiloBuffer(self, typeID, products=None, reactants=None,
            online=None, delta=None, value=None, full=None, timestamp=None,
            *a, **kw):
        """
        Updates an existing silo buffer.  Refer to addSiloBuffer for
        parameters and caveats.

        Intent of this method is for individual manual updates.
        """

        if typeID not in self.silos:
            raise ValueError('silo not currently tracking typeID')

        # Static, "immutable" values that need to be retained
        silo = self.silos[typeID]
        typeName = silo.typeName
        unitVolume = silo.unitVolume

        # Retain unless special circumstances or corrections are needed
        products = products or silo.products
        reactants = reactants or silo.reactants
        online = online or silo.online
        delta = delta or silo.delta
        value = value or silo.value
        full = full or silo.full

        # Values to be automatically calculated, or passed through and
        # the method will handle
        # timestamp

        silo = self.setSiloBuffer(typeID, typeName=typeName,
            unitVolume=unitVolume, products=products, reactants=reactants,
            online=online, delta=delta, value=value, full=full,
            timestamp=timestamp)
        return silo

    def getSiloLevels(self, timestamp):
        """
        Get the current silo levels

        Return value:
            The new values.  The value type should be a dict with the
            tracked item typeid as key and value as the amount to be
            assigned.
        """

        # dict comprehension
        return {key: silo.getCurrent(timestamp=timestamp).value
            for key, silo in self.silos.iteritems()}


class TowerResourceBuffer(TimedBuffer):
    """
    The base tower bay.
    """

    def __init__(self, tower=None, delta=None, timestamp=None, expiry=None,
            purpose=None, value=0, resourceTypeName=None, unitVolume=None,
            freeze=None, *a, **kw):

        self.tower = tower
        self.purpose = purpose
        self.resourceTypeName = resourceTypeName
        self.unitVolume = unitVolume

        if freeze is None:
            freeze = not self.isNormalFuel()

        if expiry is None:
            expiry = timestamp

        super(TowerResourceBuffer, self).__init__(
            delta=delta,
            # one hour
            period=3600,
            timestamp=timestamp,
            # immediately expired right after.
            expiry=expiry,
            # full consumption
            delta_min=1,
            # depletes
            delta_factor=-1,
            freeze=freeze,
            # No real upper limit due to the possibility to stuff more 
            # items into fuel bay because :ccp:
            full=sys.maxint,
            value=value,
            # Empty level always 0.  Fortunately.
            empty=0,
        )

    def isConsumingFuel(self, timestamp=None):
        # if this is orphaned, assume consuming.
        return self.tower is None or self.tower.getState(timestamp) in [
            STATE_REINFORCED, STATE_ONLINE]

    def isNormalFuel(self):
        return self.purpose == 1

    def freeze_FuelCheck(self, timestamp=None):
        # Strontium is never consumed normally - the entire buffer is
        # swallowed up all at once upon start of reinforcement cycle.
        # The exit time should be retrieved from API or entered
        # seperately as the time is highly variable.
        return not self.isConsumingFuel(timestamp) or not self.isNormalFuel()

    def getCurrent(self, *a, **kw):
        return super(TowerResourceBuffer, self).getCurrent(
            tower=self.tower,
            purpose=self.purpose,
            resourceTypeName=self.resourceTypeName,
            unitVolume=self.unitVolume,
            *a, **kw)


class TowerSiloBuffer(TimedBuffer):
    """
    The silos for towers.

    Note: due to simplicity, this class cannot be used to track
    intermediate products, only final products or source reactants.
    """

    # XXX prototype stage, ignore item volume, track with raw count.
    def __init__(self, tower=None, typeName=None, unitVolume=None,
            volume=None, products=None, reactants=None, online=True,
            # capture these here because they will be overriden.
            delta_min=None, delta_factor=None, period=None,
            *a, **kw):

        self.tower = tower
        self.typeName = typeName
        self.unitVolume = unitVolume
        # If this is to be consumed.
        self.products = products
        # reactants is list of silo ids belonging to tower that will be
        # consumed to make this.
        self.reactants = reactants
        self.online = online

        # increase if this is not used to produce stuff, decrease
        # otherwise.
        delta_factor = products is None and 1 or -1
        # partial product accumulation, no partial reactants
        delta_min = int(not (products is None))

        super(TowerSiloBuffer, self).__init__(
            # one hour
            period=3600,
            delta_min=delta_min,
            delta_factor=delta_factor,
            *a, **kw
        )

    def isOnline(self, timestamp=None):
        # if this is an orphan, assume online anyway, otherwise base on
        # tower's state.
        return self.online and (
            self.tower is None or
            self.tower.getState(timestamp) == STATE_ONLINE
        )

    def getCyclesUntilOffline(self):
        if self.tower is None:
            return sys.maxint

        timelimit = self.tower.getOfflineTimestamp()
        # truncate for maximum cycle count
        result = int((timelimit - self.timestamp) / self.period)
        return result

    def getCyclesReactants(self):
        """
        Get how many cycles the reactants can sustain the reaction to
        produce this product.
        """

        result = sys.maxint
        if (not self.products is None or self.reactants is None or
                self.tower is None):
            return result

        for typeID in self.reactants:
            target_silo = self.tower.silos.get(typeID)
            if target_silo is None:
                continue
            result = min(result, target_silo.getIndependentCyclesPossible())

        return result

    def getCyclesProducts(self):
        """
        Get how many cycles the products can be made, based on the
        amount of total reactants to make the product.
        """

        result = sys.maxint
        if (not self.reactants is None or self.products is None or
                self.tower is None):
            return result

        for typeID in self.products:
            target_silo = self.tower.silos.get(typeID)
            if target_silo is None:
                continue
            result = min(result, target_silo.getCyclesReactants())

        return result

    def getIndependentCyclesPossible(self):
        """
        Without involvement of silo dependencies
        """

        cycles_possible = super(TowerSiloBuffer, self).getCyclesPossible()
        # Have to base this on the state this was originally based on.
        if not self.isOnline(self.timestamp):
            # Can't do anything if offline...
            return 0
        cycles_till_offline = self.getCyclesUntilOffline()
        return min(cycles_possible, cycles_till_offline)

    def getCyclesPossible(self):
        default = self.getIndependentCyclesPossible()
        cycles_products = self.getCyclesProducts()
        cycles_reactants = self.getCyclesReactants()
        return min(default, cycles_products, cycles_reactants)

    def freeze_Reactants(self, timestamp):
        # Check whether reactants are out.
        return False

    def getCurrent(self, *a, **kw):
        return super(TowerSiloBuffer, self).getCurrent(
            tower=self.tower,
            typeName=self.typeName,
            unitVolume=self.unitVolume,
            products=self.products,
            reactants=self.reactants,
            online=self.online,
            *a, **kw)
