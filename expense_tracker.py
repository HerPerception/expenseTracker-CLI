from datetime import datetime
import json, sys, decimal

FILENAME = "expenses.json"

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

    for each_expense in expenses:
        try:
            parse_expense(each_expense)
        except KeyError as e:
            print(f"Expense ID {each_expense['id']} missing one or more key-value pairs.: {e}", file=sys.stderr)
            sys.exit(1)
        except decimal.InvalidOperation as e:
            print(f"Expense ID {each_expense['id']} has invalid amount.: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Expense ID {each_expense['id']} has invalid datetime value.: {e}", file=sys.stderr)
            sys.exit(1)
        
    return expenses
        