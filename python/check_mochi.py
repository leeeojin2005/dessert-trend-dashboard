import pandas as pd
m = pd.read_csv("../data/monthly_counts.csv")
m = m[m["item"] == "모찌"]
print(m[m["month"].str.endswith(("-06", "-12"))].to_string(index=False))
print(m.tail(12).to_string(index=False))