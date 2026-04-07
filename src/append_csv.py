import pandas as pd
from io import StringIO

# Notice the header row is removed from this string!
# new_records = """Waterloo & City,Mondays to Fridays,Morning Peak,2.375
# Waterloo & City,Mondays to Fridays,Midday Off-Peak,5.0
# Waterloo & City,Mondays to Fridays,Evening Peak,2.375
# Waterloo & City,Mondays to Fridays,19.45 to 21.30,3.5
# Waterloo & City,Mondays to Fridays,21.30 to 23.30,6.0
# Waterloo & City,Mondays to Fridays,23.30 to Close,10.0
# Waterloo & City,Saturdays,Start to 18.30,5.0
# Waterloo & City,Saturdays,18.30 to 23.30,6.0
# Waterloo & City,Saturdays,23.30 to Close,10.0"""

# Append directly to your existing CSV
with open('data\service_frequency.csv', 'a') as f:
    # Adding a newline before appending ensures it starts on a fresh row
    f.write(new_records)

print("Successfully appended Circle and Hammersmith & City line frequencies to service_frequency.csv")