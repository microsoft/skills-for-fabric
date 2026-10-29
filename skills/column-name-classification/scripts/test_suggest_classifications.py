import json
from pathlib import Path
import subprocess
import sys
import unittest

from refresh_catalog import parse_catalog
from suggest_classifications import CATALOG, Matcher


class ClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.matcher = Matcher(cls.catalog)

    def test_ssn_variations(self):
        for column in (
            "SSN", "ssn", "Social security number", "social_security_number",
            "SocialSecurityNumber", "socialSecurityNo", "SOCIALSECURITYNUMBER",
            "employee_ssn", "customerSSN", "SSN#", "ssn_num", "ssns", "socialsecurityno",
        ):
            with self.subTest(column=column):
                result = self.matcher.suggest(column)
                self.assertEqual(result["status"], "suggested")
                self.assertEqual(result["suggested_tag"], "Social security number")
                self.assertGreater(len(result["sit_candidates"]), 1)

    def test_credit_card_variations(self):
        for column in ("Credit card number", "credit_card_no", "creditCardNumber", "CCN", "billing_cc_num", "creditcardnbr"):
            with self.subTest(column=column):
                result = self.matcher.suggest(column)
                self.assertEqual(result["suggested_tag"], "Credit card number")
                self.assertEqual(len(result["sit_candidates"]), 1)

    def test_explicit_jurisdiction_keeps_the_specific_sit(self):
        result = self.matcher.suggest("customer_us_ssn")
        self.assertEqual(result["suggested_tag"], "Social security number")
        self.assertEqual(
            [entry["name"] for entry in result["sit_candidates"]],
            ["U.S. social security number (SSN)"],
        )

    def test_ambiguous_aliases_do_not_pick_a_category(self):
        for column in ("PAN", "customer_pan", "card_number", "ssn_credit_card_number"):
            with self.subTest(column=column):
                result = self.matcher.suggest(column)
                self.assertEqual(result["status"], "needs_review")
                self.assertIsNone(result["suggested_tag"])
                self.assertGreater(len(result["sit_candidates"]), 1)

    def test_derived_and_supporting_fields_are_not_full_values(self):
        for column in (
            "ssn_last4", "hashed_ssn", "hasSSN", "ssn_status", "ssn_token",
            "credit_card_expiry", "creditCardNumberHash", "credit_card_holder",
            "api_key_rotation_date", "soc_sec_benefit_amount", "password_hint",
        ):
            with self.subTest(column=column):
                result = self.matcher.suggest(column)
                self.assertEqual(result["status"], "needs_review")
                self.assertIsNone(result["suggested_tag"])

    def test_no_substring_or_generic_identifier_matches(self):
        for column in ("session", "session_id", "assignment", "card", "id", "number", "order_count", "CVV", "email_address"):
            with self.subTest(column=column):
                result = self.matcher.suggest(column)
                self.assertEqual(result["status"], "no_name_match")
                self.assertIsNone(result["suggested_tag"])
                self.assertIn("does not establish", result["reason"])

    def test_other_catalog_types_and_acronyms(self):
        for column, expected in (
            ("IBAN", "International banking account number (IBAN)"),
            ("SWIFT_code", "SWIFT code"),
            ("NINO", "U.K. national insurance number (NINO)"),
            ("aadhaar_number", "India unique identification (Aadhaar) number"),
            ("pwd", "General password"),
        ):
            with self.subTest(column=column):
                self.assertEqual(self.matcher.suggest(column)["suggested_tag"], expected)

    def test_every_official_name_is_recognized_without_losing_its_source(self):
        for entry in self.catalog["entries"]:
            with self.subTest(name=entry["name"]):
                result = self.matcher.suggest(entry["name"])
                self.assertEqual(result["status"], "suggested")
                self.assertIn(entry, result["sit_candidates"])

    def test_read_only_output_preserves_order_duplicates_and_table(self):
        result = self.matcher.classify({"table": "Customers", "columns": ["SSN", "id", "SSN"]})
        self.assertEqual(result["table"], "Customers")
        self.assertEqual([row["column"] for row in result["results"]], ["SSN", "id", "SSN"])
        self.assertFalse(result["changes_applied"])
        self.assertFalse(result["contents_inspected"])
        self.assertTrue(all(row["requires_review"] for row in result["results"]))

    def test_invalid_input_is_explicit(self):
        for payload in ({}, [], {"columns": "ssn"}, ["", "ssn"], [1], {"table": 42, "columns": ["SSN"]}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.matcher.classify(payload)

    def test_cli_returns_json_and_rejects_invalid_json(self):
        script = Path(__file__).with_name("suggest_classifications.py")
        result = subprocess.run(
            [sys.executable, str(script)], input='["ssn","credit_card_number","id"]',
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout)["results"][0]["suggested_tag"], "Social security number")
        result = subprocess.run(
            [sys.executable, str(script)], input="{invalid", text=True, capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)

    def test_catalog_parser_preserves_distinct_types_sharing_a_page(self):
        html = (
            '<a href="sit-defn-credit-card-number">Credit card number</a>'
            '<a href="sit-defn-us-social-security-number">U.S. social security number (SSN)</a>'
            '<a href="sit-defn-australia-business-number">Australian Business Number</a>'
            '<a href="sit-defn-australia-business-number">Australian Company Number</a>'
        )
        self.assertEqual(len(parse_catalog(html)), 4)
        with self.assertRaises(ValueError):
            parse_catalog('<a href="unrelated">Unrelated page</a>')


if __name__ == "__main__":
    unittest.main()
