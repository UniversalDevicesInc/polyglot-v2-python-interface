import unittest
import polyinterface

class TestPoly(unittest.TestCase):

    def test_poly(self):
        polyglot = polyinterface.Interface('Test')
        self.assertIsInstance(polyglot, polyinterface.Interface)


if __name__ == "__main__":
    unittest.main()
