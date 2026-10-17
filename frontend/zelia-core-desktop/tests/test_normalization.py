import unittest
from normalization import normalize_answer

class TestNormalization(unittest.TestCase):
    def test_int(self):
        self.assertEqual(normalize_answer("int", "50"), 50)
        self.assertEqual(normalize_answer("int", "I am 50 years old"), 50)
        self.assertIsNone(normalize_answer("int", "unknown"))

    def test_bool(self):
        self.assertTrue(normalize_answer("bool", "yes"))
        self.assertTrue(normalize_answer("bool", "aama"))
        self.assertFalse(normalize_answer("bool", "no"))
        self.assertFalse(normalize_answer("bool", "illai"))

    def test_select(self):
        self.assertEqual(normalize_answer("select", "Male"), "male")

if __name__ == '__main__':
    unittest.main()
