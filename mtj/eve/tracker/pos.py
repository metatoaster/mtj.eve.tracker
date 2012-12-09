import sys

from mtj.multimer.buffer import TimedBuffer
from mtj.multimer.timeline import Event
from mtj.multimer.installation import Installation, InstallationFactory


class SovChangeEvent(Event):
    """
    Update fuel consumption based on the new sovereignty state.
    """


class Reinforcement(Event):
    """
    Initiate strontium consumption and 
    Double fuel consu
    """


def lookupTower(itemid):
    # XXX placeholder
    items = {
        12235: {
            'name': 'Amarr Control Tower',
            'fuelname': 'Amarr Fuel Block',
            'fuelrate': 40,
        }
    }

    return items.get(itemid, {})


class TowerFactory(InstallationFactory):
    """
    Factory to build a POS.
    """

    def __init__(self):
        pass
    
    def __call__(self, system, planet, moon, state, itemid):

        info = lookupTower(itemid)

        tower = Tower(system, planet, moon, state)
        # register this into the database.

        tower.itemid = itemid

        return tower


class Tower(Installation):
    """
    A Player Owned Structure (POS).
    """

    def __init__(self, system, planet, moon, state):
        """
        This should only be called once.
        """

        self.system = system
        self.planet = planet
        self.moon = moon
        # one of {unanchored, anchoring, anchored, online, reinforced}
        self.state = state

        # Can be updated, but generally derived from evedb
        self.empire = None  # derived from system/evedb
        self.itemid = None  # tower typeid
        self.itemname = None  # derived, 'Amarr Control Tower'
        self.fuelid = None  # derived, 4548 (?)
        self.fuelname = None  # derived, 'Amarr Fuel Block'
        self.fuelrate = None  # derived, 'Amarr Fuel Block'

        # demo
        self.empire = False
        self.itemname = 'Amarr Control Tower'
        self.fuelname = 'Amarr Fuel Block'
        self.base_fuel_rate = 40

        # delta is determined by the tower (or this parent), but still
        # have to be provided as a standard parameter (rather than a
        # calculated one) to satisfy parent class invariants.
        # if for whatever reason a delta mismatch occurs due to API
        # mismatch, tower size mismatch, sov status mismatch there 
        # should be a way to override the delta until the condition
        # triggering this is corrected.

        fuel_rate = self.fuel_rate

        # The calculated moving parts
        self.resources = {
            self.fuelname: TowerResourceBuffer(self, delta, None, 0),
            'Strontium': TowerResourceBuffer(self, 1, None, 0, freeze=True),
        }

        if self.empire:
            self.resources.update({
                'charter': TowerResourceBuffer(self, delta, None, 0),
            })

    @property
    def fuel_rate(self):
        return self.base_fuel_rate

    def updateResources(self):
        raise NotImplementedError()

        # loop through all resources
        # while doing that, check that the states are consistent with
        # what the tower is representing
        # commit the states if they differ.


class TowerResourceBuffer(TimedBuffer):
    """
    The base tower bay.
    """

    def __init__(self, tower=None, delta=None, timestamp=None, value=0, 
            *a, **kw):

        self.tower = tower

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


class TowerStrontiumBuffer(TowerResourceBuffer):

    def __init__(self, tower=None, delta=None, timestamp=None, value=0, 
            *a, **kw):

        self.tower = tower

        super(TowerResourceBuffer, self).__init__(
            # Always unit size 1
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

    def isReinforced(self):
        return self.tower.state == 'reinforced'


def reinforceTower(tower):
    tower.getResourceBay('Strontium')
