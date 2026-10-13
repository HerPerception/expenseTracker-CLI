import unittest
from unittest.mock import patch, mock_open
import decimal
import json
import argparse
from datetime import datetime
from pathlib import Path

# Import your exact production functions from expense_tracker.py
from expense_tracker import (
    parse_expense, 
    load_expenses, 
    save_expenses,
    parse_amount,
    parse_description,
    generate_id,
    add_expense
)

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
        with patch("sys.stderr.write"):
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
        self.assertIsNone(result)
        mock_file.assert_called_with(Path("mock_save.json.tmp"), "w", encoding="utf-8")

    # ==========================================
    # 4. TESTS FOR parse_amount
    # ==========================================

    def test_parse_amount_valid(self):
        """Should return a Decimal object for clean valid amounts."""
        self.assertEqual(parse_amount("20.50"), decimal.Decimal("20.50"))
        self.assertEqual(parse_amount("10"), decimal.Decimal("10"))

    def test_parse_amount_not_a_number(self):
        """Should raise ArgumentTypeError if input isn't a valid numeric string."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("abc")
        self.assertEqual(str(ctx.exception), "Amount must be a number.")

    def test_parse_amount_infinite(self):
        """Should raise ArgumentTypeError if input represents Infinity or NaN."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("Infinity")
        self.assertEqual(str(ctx.exception), "Amount must be a finite number.")

    def test_parse_amount_negative_or_zero(self):
        """Should raise ArgumentTypeError if input is 0 or less."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("0")
        self.assertEqual(str(ctx.exception), "Amount must be greater than zero.")

        with self.assertRaises(argparse.ArgumentTypeError):
            parse_amount("-5.25")

    def test_parse_amount_too_many_decimals(self):
        """Should raise InvalidOperation if there are more than 2 decimal places."""
        with self.assertRaises(decimal.InvalidOperation) as ctx:
            parse_amount("12.555")
        self.assertEqual(str(ctx.exception), "amount cannot have more than 2 decimal places.")

    # ==========================================
    # 5. TESTS FOR parse_description
    # ==========================================

    def test_parse_description_valid(self):
        """Should return the cleaned up, stripped string description."""
        self.assertEqual(parse_description("  Lunch item  "), "Lunch item")

    def test_parse_description_empty(self):
        """Should raise ArgumentTypeError if the input description is empty or whitespace."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_description("   ")
        self.assertEqual(str(ctx.exception), "Description can not be empty.")

    # ==========================================
    # 6. TESTS FOR generate_id
    # ==========================================

    def test_generate_id_empty_list(self):
        """Should return 1 if there are no existing expenses."""
        self.assertEqual(generate_id([]), 1)

    def test_generate_id_increment(self):
        """Should look up the maximum ID present and increment it by 1."""
        mock_expenses = [
            {"id": 1, "description": "Coffee"},
            {"id": 4, "description": "Gas"},
            {"id": 2, "description": "Snack"}
        ]
        self.assertEqual(generate_id(mock_expenses), 5)

    # ==========================================
    # 7. TESTS FOR add_expense
    # ==========================================

    @patch("expense_tracker.datetime")
    def test_add_expense_appends_correctly(self, mock_datetime):
        """Should build an expense dict, set match times, and append to the list."""
        fixed_now = datetime(2026, 10, 13, 13, 30, 0)
        mock_datetime.now.return_value = fixed_now

        expenses_list = []
        target_amount = decimal.Decimal("45.00")
        
        result = add_expense(expenses_list, "Groceries", target_amount)

        expected_expense = {
            "id": 1,
            "description": "Groceries",
            "amount": target_amount,
            "created_at": fixed_now,
            "updated_at": fixed_now
        }

        self.assertEqual(result, expected_expense)
        self.assertEqual(len(expenses_list), 1)
        self.assertEqual(expenses_list[0], expected_expense)


if __name__ == "__main__":
    with patch("builtins.open", mock_open(read_data="")), patch("sys.stderr.write"):
        unittest.main()
