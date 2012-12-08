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


class TowerFactory(InstallationFactory):
    """
    Factory to build a POS.
    """

    def __init__(self):
        pass
    
    def __call__(self, system, planet, moon):
        tower = Tower(system, planet, moon)
        tower.system = system
        tower.planet = planet
        tower.moon = moon
        return tower


class Tower(Installation):
    """
    A Player Owned Structure (POS).
    """

    def __init__(self, system, planet, moon):
        pass


class TowerFuelBay(TimedBuffer):

    def __init__(self, value, size):
        """
        """

        # delta is variable, as determined by size (immutable) and sov
        # status.
        delta = 40

        # if for whatever reason a delta need to be forced (due to API
        # mismatch, tower size mismatch, sov status mismatch) this can
        # be overridden using this.  Use an event.
        force_delta = None

        super(TowerFuelBay, self).__init__(
            delta=delta,
            period=3600,
            timestamp=None,
            delta_min=1,  # full consumption
            delta_factor=-1,  # depletes
            freeze=False,
            extra_freeze_condition=None,
            full=sys.maxint,  # No real upper limit, it depletes anyway
            value=value,
            empty=0,
        )
