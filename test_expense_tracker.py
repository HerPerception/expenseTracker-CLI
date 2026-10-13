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
    add_expense,
    format_date,
    format_amount,
    calculate_description_width,
    print_expense,
    list_expenses,
)


class TestExpenseTracker(unittest.TestCase):

    def setUp(self):
        # Raw input dictionary matching what parse_expense expects
        self.raw_expense = {
            "id": 1,
            "description": "Lunch",
            "amount": "20.00",
            "created_at": "2026-10-13T12:00:00.000000",
            "updated_at": "2026-10-13T12:00:00.000000",
        }

        # Pre-parsed dictionary matching what save_expenses expects
        self.parsed_expense = {
            "id": 1,
            "description": "Lunch",
            "amount": decimal.Decimal("20.00"),
            "created_at": datetime.fromisoformat("2026-10-13T12:00:00.000000"),
            "updated_at": datetime.fromisoformat("2026-10-13T12:00:00.000000"),
        }

    # ==========================================
    # 1. TESTS FOR parse_expense
    # ==========================================

    def test_parse_expense_success(self):
        """Should convert amount and date strings into Decimal and datetime objects."""
        result = parse_expense(self.raw_expense)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["description"], "Lunch")
        self.assertEqual(result["amount"], decimal.Decimal("20.00"))
        self.assertIsInstance(result["created_at"], datetime)
        self.assertIsInstance(result["updated_at"], datetime)

    def test_parse_expense_missing_each_required_key(self):
        """Should raise KeyError if any required key is missing."""
        for key in ("id", "description", "amount", "created_at", "updated_at"):
            with self.subTest(missing_key=key):
                bad_expense = self.raw_expense.copy()
                del bad_expense[key]

                with self.assertRaises(KeyError) as ctx:
                    parse_expense(bad_expense)

                self.assertEqual(ctx.exception.args[0], key)

    def test_parse_expense_invalid_amount(self):
        """Should raise InvalidOperation when the amount is not numeric."""
        bad_expense = self.raw_expense.copy()
        bad_expense["amount"] = "not-a-number"

        with self.assertRaises(decimal.InvalidOperation):
            parse_expense(bad_expense)

    def test_parse_expense_non_finite_amount(self):
        """Should reject Infinity, -Infinity, and NaN."""
        for amount in ("Infinity", "-Infinity", "NaN"):
            with self.subTest(amount=amount):
                bad_expense = self.raw_expense.copy()
                bad_expense["amount"] = amount

                with self.assertRaises(decimal.InvalidOperation):
                    parse_expense(bad_expense)

    def test_parse_expense_invalid_created_at(self):
        """Should raise ValueError for an invalid created_at datetime."""
        bad_expense = self.raw_expense.copy()
        bad_expense["created_at"] = "not-a-date"

        with self.assertRaises(ValueError):
            parse_expense(bad_expense)

    def test_parse_expense_invalid_updated_at(self):
        """Should raise ValueError for an invalid updated_at datetime."""
        bad_expense = self.raw_expense.copy()
        bad_expense["updated_at"] = "not-a-date"

        with self.assertRaises(ValueError):
            parse_expense(bad_expense)

    # ==========================================
    # 2. TESTS FOR load_expenses
    # ==========================================

    def test_load_expenses_file_not_found(self):
        """Should return an empty list if the file does not exist."""
        with patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(load_expenses("non_existent_file.json"), [])

    @patch("builtins.open", new_callable=mock_open, read_data="   \n ")
    def test_load_expenses_empty_file(self, mock_file):
        """Should return an empty list when the file contains only whitespace."""
        result = load_expenses("mock_empty.json")

        self.assertEqual(result, [])
        mock_file.assert_called_once_with(
            "mock_empty.json", "r", encoding="utf-8"
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id": 1, "description": "Lunch", "amount": "20.00", '
                  '"created_at": "2026-10-13T12:00:00.000000", '
                  '"updated_at": "2026-10-13T12:00:00.000000"}]',
    )
    def test_load_expenses_success(self, mock_file):
        """Should load valid JSON and parse each expense."""
        result = load_expenses("mock_valid.json")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["amount"], decimal.Decimal("20.00"))
        self.assertIsInstance(result[0]["created_at"], datetime)

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json string")
    def test_load_expenses_invalid_json(self, mock_file):
        """Should exit with status 1 and report invalid JSON."""
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_corrupt.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    @patch("builtins.open", new_callable=mock_open, read_data='{"id": 1}')
    def test_load_expenses_json_is_not_a_list(self, mock_file):
        """Should exit if the JSON top-level value is not a list."""
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_object.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": 1}, "bad item"]')
    def test_load_expenses_item_is_not_dictionary(self, mock_file):
        """Should exit if any item in the JSON list is not a dictionary."""
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_bad_item.json")

        self.assertEqual(ctx.exception.code, 1)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id": 1, "description": "Lunch", "created_at": '
                  '"2026-10-13T12:00:00", "updated_at": "2026-10-13T12:00:00"}]',
    )
    def test_load_expenses_missing_required_key(self, mock_file):
        """Should exit if an expense is missing a required key."""
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_missing_key.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id": 1, "description": "Lunch", "amount": "abc", '
                  '"created_at": "2026-10-13T12:00:00", '
                  '"updated_at": "2026-10-13T12:00:00"}]',
    )
    def test_load_expenses_invalid_amount(self, mock_file):
        """Should exit if an expense has an invalid amount."""
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_invalid_amount.json")

        self.assertEqual(ctx.exception.code, 1)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='[{"id": 1, "description": "Lunch", "amount": "20.00", '
                  '"created_at": "bad-date", "updated_at": "2026-10-13T12:00:00"}]',
    )
    def test_load_expenses_invalid_datetime(self, mock_file):
        """Should exit if an expense contains an invalid datetime."""
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_invalid_datetime.json")

        self.assertEqual(ctx.exception.code, 1)

    def test_load_expenses_os_error(self):
        """Should exit with status 1 if opening the file raises an OS error."""
        with patch("builtins.open", side_effect=PermissionError("permission denied")):
            with patch("sys.stderr.write"):
                with self.assertRaises(SystemExit) as ctx:
                    load_expenses("unreadable.json")

        self.assertEqual(ctx.exception.code, 1)

    # ==========================================
    # 3. TESTS FOR save_expenses
    # ==========================================

    @patch("os.replace")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_expenses_success(self, mock_file, mock_mkdir, mock_replace):
        """Should serialize Decimal and datetime values and replace the target file."""
        result = save_expenses([self.parsed_expense], "mock_save.json")

        self.assertIsNone(result)
        mock_file.assert_called_once_with(
            Path("mock_save.json.tmp"), "w", encoding="utf-8"
        )
        mock_replace.assert_called_once_with(
            Path("mock_save.json.tmp"), Path("mock_save.json")
        )

        written_text = "".join(
            call.args[0]
            for call in mock_file().write.call_args_list
            if call.args
        )
        saved = json.loads(written_text)
        self.assertEqual(saved[0]["amount"], "20.00")
        self.assertEqual(saved[0]["created_at"], "2026-10-13T12:00:00")
        self.assertEqual(saved[0]["updated_at"], "2026-10-13T12:00:00")

    @patch("os.replace", side_effect=OSError("disk error"))
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_expenses_os_error(self, mock_file, mock_mkdir, mock_replace):
        """Should exit with status 1 and report an OS error during saving."""
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                save_expenses([self.parsed_expense], "mock_save.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    # ==========================================
    # 4. TESTS FOR parse_amount
    # ==========================================

    def test_parse_amount_valid(self):
        """Should return a Decimal for valid amounts."""
        self.assertEqual(parse_amount("20.50"), decimal.Decimal("20.50"))
        self.assertEqual(parse_amount("10"), decimal.Decimal("10"))

    def test_parse_amount_not_a_number(self):
        """Should raise ArgumentTypeError if input is not numeric."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("abc")

        self.assertEqual(str(ctx.exception), "Amount must be a number.")

    def test_parse_amount_non_finite(self):
        """Should reject Infinity, -Infinity, and NaN."""
        for amount in ("Infinity", "-Infinity", "NaN"):
            with self.subTest(amount=amount):
                with self.assertRaises(argparse.ArgumentTypeError) as ctx:
                    parse_amount(amount)

                self.assertEqual(
                    str(ctx.exception), "Amount must be a finite number."
                )

    def test_parse_amount_negative_or_zero(self):
        """Should reject zero and negative amounts."""
        for amount in ("0", "-5.25"):
            with self.subTest(amount=amount):
                with self.assertRaises(argparse.ArgumentTypeError) as ctx:
                    parse_amount(amount)

                self.assertEqual(
                    str(ctx.exception), "Amount must be greater than zero."
                )

    def test_parse_amount_too_many_decimal_places(self):
        """Should raise ArgumentTypeError if there are more than 2 decimal places."""
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("12.555")

        self.assertEqual(
            str(ctx.exception),
            "amount cannot have more than 2 decimal places.",
        )

    def test_parse_amount_trailing_zero_beyond_two_places(self):
        """Should reflect the current implementation's exponent-based precision rule."""
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_amount("1.230")

    # ==========================================
    # 5. TESTS FOR parse_description
    # ==========================================

    def test_parse_description_valid(self):
        """Should strip whitespace around a valid description."""
        self.assertEqual(parse_description("  Lunch item  "), "Lunch item")

    def test_parse_description_empty(self):
        """Should reject an empty or whitespace-only description."""
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
        """Should return the highest existing ID plus one."""
        mock_expenses = [
            {"id": 1, "description": "Coffee"},
            {"id": 4, "description": "Gas"},
            {"id": 2, "description": "Snack"},
        ]

        self.assertEqual(generate_id(mock_expenses), 5)

    # ==========================================
    # 7. TESTS FOR add_expense
    # ==========================================

    @patch("expense_tracker.datetime")
    def test_add_expense_appends_correctly(self, mock_datetime):
        """Should create an expense with matching timestamps and append it."""
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
            "updated_at": fixed_now,
        }

        self.assertEqual(result, expected_expense)
        self.assertEqual(len(expenses_list), 1)
        self.assertEqual(expenses_list[0], expected_expense)

    def test_add_expense_uses_next_id(self):
        """Should use the highest existing ID plus one."""
        expenses_list = [{"id": 2}, {"id": 4}]

        result = add_expense(
            expenses_list, "Groceries", decimal.Decimal("45.00")
        )

        self.assertEqual(result["id"], 5)
        self.assertEqual(len(expenses_list), 3)

    # ==========================================
    # 8. TESTS FOR FORMATTING HELPERS
    # ==========================================

    def test_format_date(self):
        """Should format a datetime as YYYY-MM-DD."""
        date_value = datetime.fromisoformat("2026-10-13T12:30:00")
        self.assertEqual(format_date(date_value), "2026-10-13")

    def test_format_amount(self):
        """Should format an amount with a dollar sign and two decimal places."""
        self.assertEqual(format_amount(decimal.Decimal("20")), "$20.00")
        self.assertEqual(format_amount(decimal.Decimal("1234.5")), "$1,234.50")

    def test_calculate_description_width(self):
        """Should use the longest description or the header width, whichever is larger."""
        expenses = [
            {"description": "Tea"},
            {"description": "A longer description"},
        ]

        self.assertEqual(
            calculate_description_width(expenses),
            len("A longer description"),
        )

    def test_calculate_description_width_empty_list(self):
        """Should return the header width when the expense list is empty."""
        self.assertEqual(
            calculate_description_width([]), len("Description")
        )

    # ==========================================
    # 9. TESTS FOR print_expense
    # ==========================================

    @patch("builtins.print")
    def test_print_expense(self, mock_print):
        """Should print the expense with its ID, date, description, and amount."""
        print_expense(self.parsed_expense, len("Description"))

        mock_print.assert_called_once_with(
            "ID: 1 || Date: 2026-10-13 || Description: Lunch       || Amount: $20.00"
        )

    # ==========================================
    # 10. TESTS FOR list_expenses
    # ==========================================

    @patch("builtins.print")
    def test_list_expenses_empty(self, mock_print):
        """Should print a message if there are no expenses."""
        result = list_expenses([])

        self.assertIsNone(result)
        mock_print.assert_called_once_with("No expenses found.")

    @patch("expense_tracker.print_expense")
    def test_list_expenses_calls_print_expense_for_each_item(self, mock_print_expense):
        """Should print every expense when the list is not empty."""
        expenses = [
            self.parsed_expense,
            {
                **self.parsed_expense,
                "id": 2,
                "description": "Transport",
                "amount": decimal.Decimal("10.00"),
            },
        ]

        result = list_expenses(expenses)

        self.assertIsNone(result)
        self.assertEqual(mock_print_expense.call_count, 2)


if __name__ == "__main__":
    unittest.main()