from unittest import TestCase, mock
from polyinterface import LOGGER, PolyInterface, Interface
import os

class TestPoly(TestCase):


    def test_poly(self):
        with self.assertRaises(SystemExit):
            polyglot = Interface('Test')


class TestPolyInstance(TestCase):

    @mock.patch.dict(os.environ,{'PROFILE_NUM':'1234'})
    def setUp(self):
        self.polyglot = Interface('Test')

    def test_init(self):
        self.assertIsInstance(self.polyglot, Interface)
