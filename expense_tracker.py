from datetime import datetime
from pathlib import Path
import decimal, json, sys, os, argparse

FILENAME = Path(__file__).parent / ".expenses-data" / "expenses.json"
REQUIRED_KEYS = ("id", "description", "amount", "created_at", "updated_at")


def parse_expense(expense):
    for key in REQUIRED_KEYS:
        if key not in expense:
            raise KeyError(key)
    amount = decimal.Decimal(expense["amount"])
    if not amount.is_finite():
        raise decimal.InvalidOperation("amount must be a finite number.")
    return {
        "id": expense["id"],
        "description": expense["description"],
        "amount": amount,
        "created_at": datetime.fromisoformat(expense["created_at"]),
        "updated_at": datetime.fromisoformat(expense["updated_at"]),
    }
   
def load_expenses(filename=FILENAME):
    
    try:
        with open(filename, 'r', encoding="utf-8") as file:
            file_content = file.read()
    except FileNotFoundError:
        return []
    except OSError as e:
        print(f"Error. File may have no read permission or there's a problem with the file.: {e}", file=sys.stderr)
        sys.exit(1)

    if len(file_content.strip()) == 0:
        return []
    try:
        expenses = json.loads(file_content)
    except json.JSONDecodeError as e:
        print(f"Error: {filename} may contain invalid json: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not isinstance(expenses, list):
        print(f"Expected type=list for file: {filename}, got {type(expenses).__name__}", file=sys.stderr)
        sys.exit(1)
    all_valid_dicts = all(isinstance(expense, dict) for expense in expenses)
    if not all_valid_dicts:
        print(f"{filename} should be a list of dictionaries. One or more expenses are not valid dictionaries.", file=sys.stderr)
        sys.exit(1)

    parsed_expenses = []
    for position, each_expense in enumerate(expenses, start=1):
        label = each_expense.get("id", f"at position {position}")
        try:
            parsed_expenses.append(parse_expense(each_expense))
        except KeyError as e:
            print(f"Expense {label} is missing a key: {e}", file=sys.stderr)
            sys.exit(1)
        except decimal.InvalidOperation as e:
            print(f"Expense {label} has an invalid amount: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Expense {label} has an invalid datetime value: {e}", file=sys.stderr)
            sys.exit(1)
        except TypeError as e:
            print(f"Expense {label} value has the wrong type: {e}", file=sys.stderr)
            sys.exit(1)

    return parsed_expenses


def save_expenses(expenses, filename=FILENAME):
    updated_expenses = []
    for expense in expenses:
        new_expense = {
            "id": expense["id"],
            "description": expense["description"],
            "amount": str(expense["amount"]),
            "created_at": expense["created_at"].isoformat(),
            "updated_at": expense["updated_at"].isoformat(),
        }
        updated_expenses.append(new_expense)

    filepath = Path(filename)
    temp_file = filepath.with_suffix(filepath.suffix + ".tmp")
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(updated_expenses, file, indent=4)
        os.replace(temp_file, filepath)
    except OSError as e:
        print(f"Error: Failed to save expenses to {filepath} due to an error: {e}", file=sys.stderr)
        # Safely attempts to delete the file. If it's already missing, it ignores the error.
        temp_file.unlink(missing_ok=True)
        sys.exit(1)

#Helper functions for add_expense
def parse_amount(input_amount):
    try:
        input_amount = decimal.Decimal(input_amount)
    except decimal.InvalidOperation:
        raise argparse.ArgumentTypeError("Amount must be a number.")
    if not input_amount.is_finite():
        raise argparse.ArgumentTypeError("Amount must be a finite number.")
    if input_amount <= 0 :
        raise argparse.ArgumentTypeError("Amount must be greater than zero.")
    if input_amount.as_tuple().exponent < -2:
        raise argparse.ArgumentTypeError("amount cannot have more than 2 decimal places.")
    return input_amount

def parse_description(input_text):
    description = input_text.strip()
    if not description:
        raise argparse.ArgumentTypeError("Description can not be empty.")
    return description

def generate_id(expenses):
    highest_id = max((expense['id'] for expense in expenses), default=0)
    return highest_id + 1

def add_expense(expenses, description, amount):
    created_at = datetime.now()
    new_expense = {
            "id": generate_id(expenses),
            "description": description,
            "amount": amount,
            "created_at": created_at,
            "updated_at": created_at,
        }
    expenses.append(new_expense)
    return new_expense


#Helper functions for list_expenses()
def format_date(date_val):
    """Takes a datetime or date object and returns YYYY-MM-DD."""
    return date_val.strftime("%Y-%m-%d")

def format_amount(amount):
    """Takes a Decimal amount and returns a formatted currency string."""
    return  f"${amount:,.2f}"

def calculate_description_width(expenses):
    desc_width = max(len("Description"), max((len(str(expense["description"])) for expense in expenses), default=0))
    return desc_width

def print_expense(expense, desc_width):
    expense_id = expense["id"]
    description = expense["description"]
    amount = format_amount(expense["amount"])
    date = format_date(expense["created_at"])
    print(f"ID: {expense_id} || Date: {date} || Description: {description:<{desc_width}} || Amount: {amount}")

def list_expenses(expenses):
    if not expenses:
        print("No expenses found.")
        return
    description_width = calculate_description_width(expenses)
    for expense in expenses:
        print_expense(expense, description_width)



