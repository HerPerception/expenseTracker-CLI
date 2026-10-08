from datetime import datetime
import argparse
import json
date = datetime.now().isoformat()
date = datetime.now().strftime(date)
print(date)
date = datetime.now().isoformat()
date = datetime.fromisoformat(date)
date = datetime.month
print(date)
date = datetime.now().isoformat()
date = datetime.now().fromisoformat(date)
print(date)
date = datetime.now().isoformat()
date_dict = {"date": date}
jsonformat = json.dumps(date_dict)
print(jsonformat)
this_year = datetime.now().year
print(this_year)
this_month = datetime.now().month
print(this_month)
today = datetime.now().day
print(today)

class CustomParser(argparse.ArgumentParser):

    def error(self, message):
        print("Input is not a valid month number!")
        self.exit(2)

def valid_month(month_val):
    try:
        month = int(month_val)
    except ValueError:
        raise argparse.ArgumentTypeError("Input is not a valid month number!")
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("Input is not a valid month number!")
    return month
parser = CustomParser()
parser.add_argument(
    "--month",
    type=valid_month
    )
arg = parser.parse_args()
print(arg.month)

