from datetime import datetime
import json, sys, decimal

FILENAME = "expenses.json"

# def parse_expense(expense):
#     amount = expense["amount"]
#     try:
#         amount = decimal.Decimal(amount)
#         expense["amount"] = amount
#     except decimal.InvalidOperation:
#         raise
   
REQUIRED_KEYS = ("id", "description", "amount", "created_at", "updated_at")


def parse_expense(expense):
    for key in REQUIRED_KEYS:
        if key not in expense:
            raise KeyError(key)

    return {
        "id": expense["id"],
        "description": expense["description"],
        "amount": decimal.Decimal(expense["amount"]),
        "created_at": datetime.fromisoformat(expense["created_at"]),
        "updated_at": datetime.fromisoformat(expense["updated_at"]),
    }
   
def load_expenses(filename):
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
        except (ValueError, TypeError) as e:
            print(f"Expense {label} has an invalid datetime value: {e}", file=sys.stderr)
            sys.exit(1)

    return parsed_expenses

print(load_expenses(FILENAME))