import unittest
from unittest.mock import patch, mock_open
import decimal
import json
import argparse
from datetime import datetime
from pathlib import Path

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
    parse_id,
    find_expense,
    delete_expense,
    parse_month,
    calculate_total,
    build_parser,
)


class TestExpenseTracker(unittest.TestCase):

    def setUp(self):
        self.raw_expense = {
            "id": 1,
            "description": "Lunch",
            "amount": "20.00",
            "created_at": "2026-10-13T12:00:00.000000",
            "updated_at": "2026-10-13T12:00:00.000000",
        }

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
        result = parse_expense(self.raw_expense)

        self.assertEqual(result["id"], 1)
        self.assertEqual(result["description"], "Lunch")
        self.assertEqual(result["amount"], decimal.Decimal("20.00"))
        self.assertIsInstance(result["created_at"], datetime)
        self.assertIsInstance(result["updated_at"], datetime)

    def test_parse_expense_missing_each_required_key(self):
        for key in ("id", "description", "amount", "created_at", "updated_at"):
            with self.subTest(missing_key=key):
                bad_expense = self.raw_expense.copy()
                del bad_expense[key]

                with self.assertRaises(KeyError) as ctx:
                    parse_expense(bad_expense)

                self.assertEqual(ctx.exception.args[0], key)

    def test_parse_expense_invalid_amount(self):
        bad_expense = self.raw_expense.copy()
        bad_expense["amount"] = "not-a-number"

        with self.assertRaises(decimal.InvalidOperation):
            parse_expense(bad_expense)

    def test_parse_expense_non_finite_amount(self):
        for amount in ("Infinity", "-Infinity", "NaN"):
            with self.subTest(amount=amount):
                bad_expense = self.raw_expense.copy()
                bad_expense["amount"] = amount

                with self.assertRaises(decimal.InvalidOperation):
                    parse_expense(bad_expense)

    def test_parse_expense_invalid_created_at(self):
        bad_expense = self.raw_expense.copy()
        bad_expense["created_at"] = "not-a-date"

        with self.assertRaises(ValueError):
            parse_expense(bad_expense)

    def test_parse_expense_invalid_updated_at(self):
        bad_expense = self.raw_expense.copy()
        bad_expense["updated_at"] = "not-a-date"

        with self.assertRaises(ValueError):
            parse_expense(bad_expense)

    # ==========================================
    # 2. TESTS FOR load_expenses
    # ==========================================

    def test_load_expenses_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            self.assertEqual(load_expenses("non_existent_file.json"), [])

    @patch("builtins.open", new_callable=mock_open, read_data="   \n ")
    def test_load_expenses_empty_file(self, mock_file):
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
        result = load_expenses("mock_valid.json")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["amount"], decimal.Decimal("20.00"))
        self.assertIsInstance(result[0]["created_at"], datetime)

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json string")
    def test_load_expenses_invalid_json(self, mock_file):
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_corrupt.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    @patch("builtins.open", new_callable=mock_open, read_data='{"id": 1}')
    def test_load_expenses_json_is_not_a_list(self, mock_file):
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_object.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": 1}, "bad item"]')
    def test_load_expenses_item_is_not_dictionary(self, mock_file):
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
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as ctx:
                load_expenses("mock_invalid_datetime.json")

        self.assertEqual(ctx.exception.code, 1)

    def test_load_expenses_os_error(self):
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
        with patch("sys.stderr.write") as mock_stderr:
            with self.assertRaises(SystemExit) as ctx:
                save_expenses([self.parsed_expense], "mock_save.json")

        self.assertEqual(ctx.exception.code, 1)
        self.assertTrue(mock_stderr.called)

    # ==========================================
    # 4. TESTS FOR parse_amount
    # ==========================================

    def test_parse_amount_valid(self):
        self.assertEqual(parse_amount("20.50"), decimal.Decimal("20.50"))
        self.assertEqual(parse_amount("10"), decimal.Decimal("10"))

    def test_parse_amount_not_a_number(self):
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("abc")

        self.assertEqual(str(ctx.exception), "Amount must be a number.")

    def test_parse_amount_non_finite(self):
        for amount in ("Infinity", "-Infinity", "NaN"):
            with self.subTest(amount=amount):
                with self.assertRaises(argparse.ArgumentTypeError) as ctx:
                    parse_amount(amount)

                self.assertEqual(
                    str(ctx.exception), "Amount must be a finite number."
                )

    def test_parse_amount_negative_or_zero(self):
        for amount in ("0", "-5.25"):
            with self.subTest(amount=amount):
                with self.assertRaises(argparse.ArgumentTypeError) as ctx:
                    parse_amount(amount)

                self.assertEqual(
                    str(ctx.exception), "Amount must be greater than zero."
                )

    def test_parse_amount_too_many_decimal_places(self):
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_amount("12.555")

        self.assertEqual(
            str(ctx.exception),
            "amount cannot have more than 2 decimal places.",
        )

    def test_parse_amount_trailing_zero_beyond_two_places(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_amount("1.230")

    # ==========================================
    # 5. TESTS FOR parse_description
    # ==========================================

    def test_parse_description_valid(self):
        self.assertEqual(parse_description("  Lunch item  "), "Lunch item")

    def test_parse_description_empty(self):
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            parse_description("   ")

        self.assertEqual(str(ctx.exception), "Description can not be empty.")

    # ==========================================
    # 6. TESTS FOR generate_id
    # ==========================================

    def test_generate_id_empty_list(self):
        self.assertEqual(generate_id([]), 1)

    def test_generate_id_increment(self):
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
        date_value = datetime.fromisoformat("2026-10-13T12:30:00")
        self.assertEqual(format_date(date_value), "2026-10-13")

    def test_format_amount(self):
        self.assertEqual(format_amount(decimal.Decimal("20")), "$20.00")
        self.assertEqual(format_amount(decimal.Decimal("1234.5")), "$1,234.50")
        self.assertEqual(format_amount(decimal.Decimal("0")), "$0.00")

    def test_calculate_description_width(self):
        expenses = [
            {"description": "Tea"},
            {"description": "A longer description"},
        ]

        self.assertEqual(
            calculate_description_width(expenses),
            len("A longer description"),
        )

    def test_calculate_description_width_empty_list(self):
        self.assertEqual(
            calculate_description_width([]), len("Description")
        )

    # ==========================================
    # 9. TESTS FOR print_expense
    # ==========================================

    @patch("builtins.print")
    def test_print_expense(self, mock_print):
        print_expense(self.parsed_expense, len("Description"))

        mock_print.assert_called_once_with(
            "ID: 1 || Date: 2026-10-13 || Description: Lunch       || Amount: $20.00    ||"
        )

    # ==========================================
    # 10. TESTS FOR list_expenses
    # ==========================================

    @patch("builtins.print")
    def test_list_expenses_empty(self, mock_print):
        result = list_expenses([])

        self.assertIsNone(result)
        mock_print.assert_called_once_with("No expenses found.")

    @patch("expense_tracker.print_expense")
    def test_list_expenses_calls_print_expense_for_each_item(self, mock_print_expense):
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

    # ==========================================
    # 11. TESTS FOR parse_id
    # ==========================================

    def test_parse_id_valid(self):
        self.assertEqual(parse_id("12"), 12)

    def test_parse_id_not_integer(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_id("abc")

    def test_parse_id_zero_or_negative(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    parse_id(value)

    # ==========================================
    # 12. TESTS FOR find_expense
    # ==========================================

    def test_find_expense_found(self):
        expenses = [self.parsed_expense]

        self.assertIs(find_expense(expenses, 1), self.parsed_expense)

    def test_find_expense_not_found(self):
        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit) as ctx:
                find_expense([self.parsed_expense], 99)

        self.assertEqual(ctx.exception.code, 1)

    # ==========================================
    # 13. TESTS FOR delete_expense
    # ==========================================

    def test_delete_expense_removes_and_returns_expense(self):
        expenses = [self.parsed_expense]

        result = delete_expense(expenses, 1)

        self.assertEqual(result, self.parsed_expense)
        self.assertEqual(expenses, [])

    def test_delete_expense_missing_id(self):
        expenses = [self.parsed_expense]

        with patch("sys.stderr.write"):
            with self.assertRaises(SystemExit):
                delete_expense(expenses, 99)

        self.assertEqual(len(expenses), 1)

    # ==========================================
    # 14. TESTS FOR parse_month
    # ==========================================

    def test_parse_month_valid(self):
        for month in range(1, 13):
            with self.subTest(month=month):
                self.assertEqual(parse_month(str(month)), month)

    def test_parse_month_not_integer(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_month("abc")

    def test_parse_month_out_of_range(self):
        for month in ("0", "13", "-1"):
            with self.subTest(month=month):
                with self.assertRaises(argparse.ArgumentTypeError):
                    parse_month(month)

    # ==========================================
    # 15. TESTS FOR calculate_total
    # ==========================================

    def make_expense(self, amount, created_at, expense_id=1):
        timestamp = datetime.fromisoformat(created_at)
        return {
            "id": expense_id,
            "description": "Test expense",
            "amount": decimal.Decimal(str(amount)),
            "created_at": timestamp,
            "updated_at": timestamp,
        }

    def test_calculate_total_empty_expenses(self):
        self.assertEqual(calculate_total([]), 0)

    def test_calculate_total_all_expenses(self):
        expenses = [
            self.make_expense("10.00", "2026-10-01T10:00:00", 1),
            self.make_expense("20.50", "2026-09-15T12:00:00", 2),
            self.make_expense("5.25", "2025-10-20T09:00:00", 3),
        ]

        self.assertEqual(
            calculate_total(expenses),
            decimal.Decimal("35.75"),
        )

    @patch("expense_tracker.datetime")
    def test_calculate_total_filters_by_month_and_current_year(self, mock_datetime):
        mock_datetime.now.return_value.year = 2026

        expenses = [
            self.make_expense("10.00", "2026-10-01T10:00:00", 1),
            self.make_expense("20.50", "2026-10-15T12:00:00", 2),
            self.make_expense("30.00", "2026-09-15T12:00:00", 3),
            self.make_expense("40.00", "2025-10-20T09:00:00", 4),
        ]

        self.assertEqual(
            calculate_total(expenses, 10),
            decimal.Decimal("30.50"),
        )

    @patch("expense_tracker.datetime")
    def test_calculate_total_no_matching_expenses_returns_zero(self, mock_datetime):
        mock_datetime.now.return_value.year = 2026

        expenses = [
            self.make_expense("10.00", "2026-09-01T10:00:00", 1),
            self.make_expense("20.00", "2025-10-15T12:00:00", 2),
        ]

        self.assertEqual(calculate_total(expenses, 10), 0)

    @patch("expense_tracker.datetime")
    def test_calculate_total_uses_current_year_each_call(self, mock_datetime):
        expenses = [
            self.make_expense("10.00", "2026-10-01T10:00:00", 1),
            self.make_expense("20.00", "2027-10-01T10:00:00", 2),
        ]

        mock_datetime.now.return_value.year = 2026
        first_total = calculate_total(expenses, 10)

        mock_datetime.now.return_value.year = 2027
        second_total = calculate_total(expenses, 10)

        self.assertEqual(first_total, decimal.Decimal("10.00"))
        self.assertEqual(second_total, decimal.Decimal("20.00"))

    # ==========================================
    # 16. TESTS FOR build_parser
    # ==========================================

    def test_build_parser_summary_without_month(self):
        args = build_parser().parse_args(["summary"])

        self.assertEqual(args.command, "summary")
        self.assertIsNone(args.month)

    def test_build_parser_summary_with_month(self):
        args = build_parser().parse_args(["summary", "--month", "10"])

        self.assertEqual(args.command, "summary")
        self.assertEqual(args.month, 10)

    def test_build_parser_summary_rejects_invalid_month(self):
        for month in ("0", "13", "abc"):
            with self.subTest(month=month):
                with self.assertRaises(SystemExit):
                    build_parser().parse_args(["summary", "--month", month])

    def test_build_parser_missing_command(self):
        """Should reject input when no command is provided."""
        with self.assertRaises(SystemExit) as ctx:
            build_parser().parse_args([])

        self.assertEqual(ctx.exception.code, 2)

    def test_build_parser_missing_command_displays_error(self):
        """Should display an error when no command is provided."""
        with patch("sys.stderr") as mock_stderr:
            with self.assertRaises(SystemExit):
                build_parser().parse_args([])

        self.assertIn(
            "the following arguments are required: command",
            "".join(
                call.args[0]
                for call in mock_stderr.write.call_args_list
                if call.args
            ),
        )

if __name__ == "__main__":
    unittest.main()