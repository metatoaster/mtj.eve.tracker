from unittest import TestCase, TestSuite, makeSuite

from mtj.eve.tracker.pos import Tower, TowerResourceBuffer, TowerSiloBuffer

FUEL_NORMAL = 1
FUEL_REINFORCE = 4

STATE_UNANCHORED = 0
STATE_ANCHORED = 1
STATE_ONLINING = 2
STATE_REINFORCE = 3
STATE_ONLINE = 4


class StructureTestCase(TestCase):
    """
    Unit tests for structures
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_0000_base_tower(self):
        tower = Tower(1000001, 12235, 30004608, 40291202, 4,
            1325376000, 1306886400, 498125261)

        self.assertEqual(tower.capacity, 140000)
        self.assertEqual(tower.strontCapacity, 50000)

    def test_1000_failure_celestial_solarsystem_mismatch(self):
        # Celestial must be located within the solar system
        pass


class TowerResourceBufferTestCase(TestCase):
    """
    Test the buffer subclass implementation.
    """

    def setUp(self):
        self.tower = type('DummyTower', (object,), {})
        self.tower.state = STATE_ONLINE

    def test_0000_basic(self):
        fuelbay = TowerResourceBuffer(self.tower, 40, 0, FUEL_NORMAL,
              28000, "Amarr Fuel Block")
        self.assertTrue(fuelbay.isConsumingFuel())
        self.assertTrue(fuelbay.isNormalFuel())
        self.assertFalse(fuelbay.freeze_FuelCheck(0))

        strontbay = TowerResourceBuffer(self.tower, 400, 0, FUEL_REINFORCE,
              9600, "Strontium Clathrates")
        self.assertTrue(strontbay.isConsumingFuel())
        self.assertFalse(strontbay.isNormalFuel())
        self.assertTrue(strontbay.freeze_FuelCheck(0))

    def test_0100_current(self):
        # even though the new clone generated by getCurrent is not used
        # by the tower as a whole, it should still be consistent with
        # expected results
        fuelbay = TowerResourceBuffer(self.tower, 40, 0, FUEL_NORMAL,
              28000, "Amarr Fuel Block")
        fuelbay1 = fuelbay.getCurrent(3600)

        self.assertEqual(fuelbay1.value, 27960)
        self.assertEqual(fuelbay1.tower, self.tower)
        self.assertEqual(fuelbay1.purpose, fuelbay.purpose)
        self.assertEqual(fuelbay1.resourceTypeName, fuelbay.resourceTypeName)
        self.assertEqual(fuelbay1.unitVolume, fuelbay.unitVolume)

        # The actual frozen state is managed in conjunction with the
        # usage of a tower.  A buffer will faithfully deplete stront
        # currently.
        strontbay = TowerResourceBuffer(self.tower, 400, 0, FUEL_REINFORCE,
              9600, "Strontium Clathrates")
        strontbay1 = strontbay.getCurrent(3600)
        self.assertEqual(strontbay1.value, 9200)

    def test_0200_offline(self):
        fuelbay0 = TowerResourceBuffer(self.tower, 40, 0, FUEL_NORMAL,
              28000, "Amarr Fuel Block")
        self.tower.state = STATE_ANCHORED
        self.assertTrue(fuelbay0.freeze_FuelCheck(0))

        # note: offline timestamp will be assumed to be at 3600
        fuelbay1 = fuelbay0.getCurrent(36000)
        fuelbay2 = fuelbay1.getCurrent(39600)

        self.assertEqual(fuelbay1.value, 27600)
        self.assertEqual(fuelbay2.value, 27600)


class TowerSiloBufferTestCase(TestCase):
    """
    Test the buffer subclass implementation.
    """

    def setUp(self):
        self.tower = Tower(1, 12235, 30004608, 40291202, 1, 0, 0, 0)
        self.tower.initFuels()

    def test_0000_basic_naked(self):
        silo = TowerSiloBuffer(None, 'Technetium', 0.8, delta=100,
            value=0, full=75000, timestamp=0)
        silo1 = silo.getCurrent(timestamp=3600)
        self.assertEqual(silo1.value, 100)
        silo2 = silo1.getCurrent(timestamp=3600000)
        self.assertEqual(silo2.value, 75000)

    def test_0100_towered_offline(self):
        silo = TowerSiloBuffer(self.tower, 'Technetium', 0.8, delta=100,
            value=0, full=75000, timestamp=0)
        silo1 = silo.getCurrent(timestamp=36000)
        self.assertEqual(silo1.value, 0)
        silo2 = silo.getCurrent(timestamp=3600)
        self.assertEqual(silo2.value, 0)

    def test_0100_towered_reinforced(self):
        # reinforced with no fuel remaining, so 1h runtime, but silo mod
        # will be offline anyway so no accumulation.
        self.tower.state = 3
        silo = TowerSiloBuffer(self.tower, 'Technetium', 0.8, delta=100,
            value=0, full=75000, timestamp=0)
        silo1 = silo.getCurrent(timestamp=36000)
        self.assertEqual(silo1.value, 0)
        silo2 = silo.getCurrent(timestamp=3600)
        self.assertEqual(silo2.value, 0)

    def test_0200_towered_online(self):
        # online with no fuel remaining, so 1h runtime.
        self.tower.state = 4
        silo = TowerSiloBuffer(self.tower, 'Technetium', 0.8, delta=100,
            value=0, full=75000, timestamp=0)
        silo1 = silo.getCurrent(timestamp=36000)
        self.assertEqual(silo1.value, 100)
        silo2 = silo.getCurrent(timestamp=3600)
        self.assertEqual(silo2.value, 100)

    def test_0201_towered_online(self):
        # online with no fuel remaining, so 1h runtime.
        self.tower.state = 4
        # However, silo wasn't online.
        silo = TowerSiloBuffer(self.tower, 'Technetium', 0.8, delta=100,
            value=0, full=75000, timestamp=0, online=False)
        silo1 = silo.getCurrent(timestamp=36000)
        self.assertEqual(silo1.value, 0)
        silo2 = silo.getCurrent(timestamp=3600)
        self.assertEqual(silo2.value, 0)

    def test_1000_towered_reactants(self):
        self.tower.state = 4
        # 16649:Technetium
        silo_t = TowerSiloBuffer(self.tower, 'Technetium', 0.8, delta=100,
            value=1000, full=25000, produces=16662, timestamp=0)
        # 16644:Platinum
        silo_p = TowerSiloBuffer(self.tower, 'Platinum', 1, delta=100,
            value=1000, full=20000, produces=16662, timestamp=0)
        # 16662:Platinum Technite
        silo_pt = TowerSiloBuffer(self.tower, 'Platinum Technite', 1, delta=100,
            value=0, full=25000, reactants=[16644, 16649], timestamp=0)

        silo_p1 = silo_p.getCurrent(timestamp=36000)
        self.assertEqual(silo_p1.value, 900)
        silo_p2 = silo_p.getCurrent(timestamp=3600)
        self.assertEqual(silo_p2.value, 900)

        silo_t1 = silo_t.getCurrent(timestamp=36000)
        self.assertEqual(silo_t1.value, 900)
        silo_t2 = silo_t.getCurrent(timestamp=3600)
        self.assertEqual(silo_t2.value, 900)

        silo_pt1 = silo_pt.getCurrent(timestamp=36000)
        self.assertEqual(silo_pt1.value, 100)
        silo_pt2 = silo_pt.getCurrent(timestamp=3600)
        self.assertEqual(silo_pt2.value, 100)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(StructureTestCase))
    suite.addTest(makeSuite(TowerResourceBufferTestCase))
    suite.addTest(makeSuite(TowerSiloBufferTestCase))
    return suite
