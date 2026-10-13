import unittest
from unittest.mock import patch, mock_open
import decimal
import json
from datetime import datetime
from pathlib import Path

# Import your exact functions
from expense_tracker import parse_expense, load_expenses, save_expenses

class TestExpenseTracker(unittest.TestCase):

    def setUp(self):
        # Raw input dictionary matching what parse_expense expects
        self.raw_expense = {
            "id": 1,
            "description": "Lunch",
            "amount": "20.00",
            "created_at": "2026-10-13T12:00:00.000000",
            "updated_at": "2026-10-13T12:00:00.000000"
        }
        
        # Pre-parsed dictionary matching what save_expenses expects
        self.parsed_expense = {
            "id": 1,
            "description": "Lunch",
            "amount": decimal.Decimal("20.00"),
            "created_at": datetime.fromisoformat("2026-10-13T12:00:00.000000"),
            "updated_at": datetime.fromisoformat("2026-10-13T12:00:00.000000")
        }

    # ==========================================
    # 1. TESTS FOR parse_expense
    # ==========================================

    def test_parse_expense_success(self):
        """Should correctly parse raw string values into Decimal and datetime objects."""
        result = parse_expense(self.raw_expense)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["amount"], decimal.Decimal("20.00"))
        self.assertIsInstance(result["created_at"], datetime)

    def test_parse_expense_infinite_amount(self):
        """Should raise InvalidOperation when amount is non-finite."""
        bad_expense = self.raw_expense.copy()
        bad_expense["amount"] = "Infinity"
        with self.assertRaises(decimal.InvalidOperation):
            parse_expense(bad_expense)

    def test_parse_expense_missing_key(self):
        """Should raise KeyError when a required key is missing."""
        bad_expense = self.raw_expense.copy()
        del bad_expense["amount"]
        with self.assertRaises(KeyError):
            parse_expense(bad_expense)

    # ==========================================
    # 2. TESTS FOR load_expenses
    # ==========================================

    def test_load_expenses_file_not_found(self):
        """Should return an empty list if the file does not exist."""
        result = load_expenses(Path("non_existent_file.json"))
        self.assertEqual(result, [])

    @patch("builtins.open", new_callable=mock_open, read_data="   ")
    def test_load_expenses_empty_file(self, mock_file):
        """Should return an empty list if the file content is empty or whitespace."""
        result = load_expenses("mock_empty.json")
        self.assertEqual(result, [])

    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": 1, "description": "Lunch", "amount": "20.00", "created_at": "2026-10-13T12:00:00.000000", "updated_at": "2026-10-13T12:00:00.000000"}]')
    def test_load_expenses_success(self, mock_file):
        """Should load and parse valid JSON data successfully."""
        result = load_expenses("mock_valid.json")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["amount"], decimal.Decimal("20.00"))

    @patch("sys.exit")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid json string")
    def test_load_expenses_invalid_json(self, mock_file, mock_exit):
        """Should call sys.exit(1) if the JSON layout is corrupted."""
        # Suppress stderr printing to keep test outputs clean
        with patch("sys.stderr.write"):
            # Since sys.exit is mocked, your code will try to continue and raise UnboundLocalError.
            # We catch that here to verify that sys.exit(1) was triggered first.
            try:
                load_expenses("mock_corrupt.json")
            except UnboundLocalError:
                pass
        
        mock_exit.assert_called_once_with(1)

    # ==========================================
    # 3. TESTS FOR save_expenses
    # ==========================================

    @patch("os.replace")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_expenses_success(self, mock_file, mock_mkdir, mock_replace):
        """Should convert native objects to strings and save them cleanly to disk."""
        result = save_expenses([self.parsed_expense], "mock_save.json")
        
        # Matches your exact code, which implicitly returns None on successful save paths
        self.assertIsNone(result)
        
        # Asserts that the code attempts to open the correct temp filename format
        mock_file.assert_called_with(Path("mock_save.json.tmp"), "w", encoding="utf-8")


if __name__ == "__main__":
    # Suppress your file's top-level print evaluations during module import
    with patch("builtins.open", mock_open(read_data="")), patch("sys.stderr.write"):
        unittest.main()
