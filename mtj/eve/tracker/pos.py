import sys

from mtj.evedb.structure import ControlTower
from mtj.evedb.map import Map

from mtj.multimer.buffer import TimedBuffer
from mtj.multimer.timeline import Event

from mtj.eve.tracker.evelink import Helper

SECONDS_PER_HOUR = 3600

pos_info = ControlTower()
eve_map = Map()
evelink_helper = Helper()


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

        # derived but fixed values
        self.resourcePulse = onlineTimestamp % SECONDS_PER_HOUR
        self.typeName = None
        self.allianceID = None
        self.celestialName = None
        self.solarSystemName = None

        # variable derived values
        self.allianceID = None
        self.sov = None

        self._setDerivedValues()

        # The calculated values
        self.fuels = {}  # fuel
        self.resources = {}  # silos

    def _setDerivedValues(self):
        # TODO error checking and other validation somewhere
        moon = eve_map.getCelestial(self.moonID)
        solar_system = eve_map.getSolarSystem(self.locationID)
        pos = pos_info.getControlTower(self.typeID)
        self.celestialName = moon['itemName']
        self.solarSystemName = solar_system['solarSystemName']
        self.typeName = pos['typeName']

        # Not calling the update method defined below as this is part of
        # initialization.
        self.allianceID = self.queryAllianceID()
        self.sov = self.querySovStatus()

    def queryAllianceID(self):
        """
        Return the alliance ID of the standing owner of this tower.
        """

        if evelink_helper.alliances.get(self.standingOwnerID):
            return self.standingOwnerID
        else:
            return evelink_helper.corporations.get(self.standingOwnerID)

    def querySovStatus(self):
        # As the API does not provide the current development index
        # of the system, so if the discount is dependent on this
        # index, it will be impossible to reliably determine whether
        # the discount is indeed applied.
        sov_info = evelink_helper.sov[self.locationID]
        return sov_info['alliance_id'] == self.allianceID

    def initFuels(self):
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

                self.setResourceBuffer(
                    bufferGroupName='fuels',
                    bufferKey=fuel['resourceTypeID'],
                    delta=fuel['quantity'],
                    timestamp=0,  # defined later
                    purpose=fuel['purpose'],
                    value=0,  # defined later
                    resourceTypeName=fuel['typeName'],
                )

    def setResourceBuffer(self, bufferGroupName, bufferKey, delta, timestamp,
            purpose, value, resourceTypeName):
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
        """

        bufferGroup = getattr(self, bufferGroupName, None)

        # TODO this should be some sort of management smarter than a
        # simple dict.
        if not isinstance(bufferGroup, dict):
            raise ValueError('`%s` is not a valid bufferGroupName' %
                bufferGroupName)

        # TODO log this action
        res_buffer = TowerResourceBuffer(self, delta, timestamp, purpose,
            value, resourceTypeName)
        # freeze consumption of stront
        res_buffer.freeze = not res_buffer.isNormalFuel()
        bufferGroup[bufferKey] = res_buffer

    def updateFuels(self):
        pass
        # Determine if discount changed by
        # - Get and store the allianceID (if applicable) XXX should be cached.
        # - Get sovereignty data from api
        # If none of these change, report fuel
        # If changed, generate event so they will be saved, and update
        # fuel rate calculations.

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

        for fuel_id, fuel_buffer in self.fuels.iteritems():
            verifier = values.get(fuel_id)
            if not verifier:
                # Can't verify against unknown.
                continue

            calculated = fuel_buffer.getCurrent(timestamp)
            if verifier != calculated.value:
                mismatches.append(fuel_id)

        return mismatches

    def updateResources(self, values, timestamp, force=False):
        mismatches = self.verifyResources(values, timestamp)
        # dict comprehension
        all_fuels = {v['resourceTypeID']: v for v in
            pos_info.getControlTowerResource(self.typeID)}

        for resourceTypeID, value in values.iteritems():
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
            )

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
            self.updateResources(values, timestamp, True)

    def resourcePulseTimestamp(self, timestamp):
        """
        Calculate the buffer pulse with the given timestamp.

        This is to ensure resource buffer timestamps are set correctly
        so that the calculated values will be synchronized with actual
        values.
        """

        return ((timestamp - timestamp % SECONDS_PER_HOUR -
            int((timestamp % SECONDS_PER_HOUR) < self.resourcePulse) *
            SECONDS_PER_HOUR) + self.resourcePulse)

    def getResources(self, timestamp):
        """
        Get the current resource levels
        """

        # everything after offline time will not be defined.
        timestamp = min(timestamp, self.getOfflineTimestamp(fuel_pair=True))

        # dict comprehension
        return {key: fuel.getCurrent(timestamp=timestamp).value
            for key, fuel in self.fuels.iteritems()}

    def getOfflineTimestamp(self, fuel_pair=False):
        """
        Figure out from all the fuels when will the pos go offline,
        which is the moment when remaining cycles is less than zero
        (or -1).

        However, for fuel pairing calculation, provide the final
        timestamp for when to deduct fuel for calculating consumption.
        """

        offlineTimestamps = []
        for key, fuel in self.fuels.iteritems():
            if not fuel.isNormalFuel():
                continue

            # cycles remaining == -1, or last fuel pairing == 0
            remaining = (fuel.getCyclesAvailable() + int(not fuel_pair)) 
            offlineTimestamps.append(remaining * fuel.period + fuel.timestamp)

        return min(offlineTimestamps)

    def getTimeRemaining(self, timestamp):
        offlineAt = self.getOfflineTimestamp()
        return max(offlineAt - timestamp, 0)

    def update(self):
        if not self.fuel:
            # fuel not initialized.  derive from database for current
            # factionID and allianceID
            self.init_fuels()

        self.update_fuels()


class TowerResourceBuffer(TimedBuffer):
    """
    The base tower bay.
    """

    def __init__(self, tower=None, delta=None, timestamp=None, purpose=None,
            value=0, resourceTypeName=None, *a, **kw):

        self.tower = tower
        self.purpose = purpose
        self.resourceTypeName = resourceTypeName

        super(TowerResourceBuffer, self).__init__(
            delta=delta,
            # one hour
            period=3600,
            timestamp=timestamp,
            # full consumption
            delta_min=1,
            # depletes
            delta_factor=-1,
            # always running, determined by below
            freeze=False,
            # No real upper limit due to the possibility to stuff more 
            # items into fuel bay because :ccp:
            full=sys.maxint,
            value=value,
            # Empty level always 0.  Fortunately.
            empty=0,
        )

    def isConsumingFuel(self):
        # if this is orphaned, assume consuming.
        return self.tower is None or self.tower.state in [3, 4]

    def isNormalFuel(self):
        return self.purpose == 1

    def freeze_FuelCheck(self, timestamp):
        # Strontium is never consumed normally - the entire buffer is
        # swallowed up all at once upon start of reinforcement cycle.
        # The exit time should be retrieved from API or entered
        # seperately as the time is highly variable.
        return not self.isConsumingFuel() and not self.isNormalFuel()
