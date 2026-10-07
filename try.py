from datetime import datetime
from argparse import parser
import json
date = datetime.now().isoformat()
date = datetime.now().strftime(date)
print(date)
date = datetime.now().isoformat()
date = datetime.fromisoformat(date)
date = datetime.month()
print(date)
date = datetime.now().isoformat()
date = datetime.now().fromisoformat(date)
print(date)
date = datetime.now().isoformat()
date_dict = {"date": date}
jsonformat = json.dumps(date_dict)
print(jsonformat)

parser.add_argument(
    "--month",
    type=int,
    choices=range(1, 13)
)