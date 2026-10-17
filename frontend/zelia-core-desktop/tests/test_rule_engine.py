import unittest
from rule_engine import RuleEngine
from schema import Profile, Scheme

class TestRuleEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RuleEngine()
        self.scheme = Scheme(
            id="test_scheme",
            name="Test",
            description="desc",
            benefits="benefits",
            conditions={
                "operator": "and",
                "rules": [
                    {"field": "age", "op": "gte", "value": 60},
                    {"field": "income", "op": "lt", "value": 5000}
                ]
            }
        )

    def test_eligible(self):
        profile = Profile(profile_data={"age": 65, "income": 4000})
        results = self.engine.evaluate(profile, [self.scheme])
        self.assertTrue(results[0].eligible)

    def test_ineligible_age(self):
        profile = Profile(profile_data={"age": 50, "income": 4000})
        results = self.engine.evaluate(profile, [self.scheme])
        self.assertFalse(results[0].eligible)
        self.assertIn("age (50) is not gte 60", results[0].reasons)

    def test_ineligible_missing_field(self):
        profile = Profile(profile_data={"age": 65})
        results = self.engine.evaluate(profile, [self.scheme])
        self.assertFalse(results[0].eligible)
        self.assertIn("Missing field: income", results[0].reasons)

if __name__ == '__main__':
    unittest.main()
