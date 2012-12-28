import sys
from math import ceil

from mtj.evedb.structure import ControlTower
from mtj.evedb.map import Map

from mtj.multimer.buffer import TimedBuffer
from mtj.multimer.timeline import Event
from mtj.multimer.installation import Installation, InstallationFactory

from mtj.eve.tracker.evelink import Helper

pos_info = ControlTower()
eve_map = Map()
evelink_helper = Helper()


class Tower(Installation):
    """
    A Player Owned Structure (POS).
    """

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
        self.typeName = None
        self.allianceID = None
        self.celestialName = None
        self.solarSystemName = None

        self._setDerivedValues()

        # variable values
        self.sov = None  # sovereignty discount

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

        # check whether standingOwnerID is already alliance or part of
        # one.
        if evelink_helper.alliances.get(self.standingOwnerID):
            self.allianceID = self.standingOwnerID
        else:
            self.allianceID = evelink_helper.corporations.get(
                self.standingOwnerID)

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
        bufferGroup[bufferKey] = res_buffer

    def updateResourceBuffer(self, bufferGroupName, bufferKey, timestamp, 
            value):

        pass

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

    def updateResources(self, values, timestamp):
        mismatches = self.verifyResources(values, timestamp)
        all_fuels = {v['resourceTypeID']: v for v in
            pos_info.getControlTowerResource(self.typeID)}
        sov_info = evelink_helper.sov[self.locationID]

        for resourceTypeID, value in values.iteritems():
            if resourceTypeID not in mismatches:
                continue

            fuel = all_fuels.get(resourceTypeID)
            # base delta
            delta = fuel['quantity']

            # Sovereignty discounts is also done here.

            # As the API does not provide the current development index
            # of the system, so if the discount is dependent on this
            # index, it will be impossible to reliably determine whether
            # the discount is indeed applied.

            if sov_info['alliance_id'] == self.allianceID:
                # TODO determine whether it's round or ceil.
                delta = int(ceil(delta * 0.75))

            self.setResourceBuffer(
                bufferGroupName='fuels',
                bufferKey=resourceTypeID,
                delta=delta,
                timestamp=timestamp,
                purpose=fuel['purpose'],
                value=value,
                resourceTypeName=fuel['typeName'],
            )

    def update(self):
        if not self.fuel:
            # fuel not initialized.  derive from database for current
            # factionID and allianceID
            self.init_fuels()

        self.update_fuels()

        # delta is determined by the tower (or this parent), but still
        # have to be provided as a standard parameter (rather than a
        # calculated one) to satisfy parent class invariants.
        # if for whatever reason a delta mismatch occurs due to API
        # mismatch, tower size mismatch, sov status mismatch there 
        # should be a way to override the delta until the condition
        # triggering this is corrected.


class TowerResourceBuffer(TimedBuffer):
    """
    The base tower bay.
    """

    def __init__(self, tower=None, delta=None, timestamp=None, purpose=None,
            value=0, resourceTypeName=None, *a, **kw):

        self.tower = tower
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
            extra_freeze_conditions=None,
            # No real upper limit due to the possibility to stuff more 
            # items into fuel bay because :ccp:
            full=sys.maxint,
            value=value,
            # Empty level always 0.  Fortunately.
            empty=0,
        )


def reinforceTower(tower):
    tower.getResourceBay('Strontium')
