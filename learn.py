import numpy as np

prices = np.array([1200, 3500, 800, 2500])
#This operation would be performed on each element without a loop.
discounted = prices * 0.9
print(discounted)

import pandas as pd
df = pd.read_csv("sales.csv")
print(df.head)