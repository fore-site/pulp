import csv
import os

SERIES = []

csv_path = os.path.join(os.path.dirname(__file__), 'test_data.csv')
with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        series = dict(row)
        # Split authors and genres into lists
        series['authors'] = [a.strip() for a in series['authors'].split(';')]
        series['genres'] = [g.strip() for g in series['genres'].split(';')]
        SERIES.append(series)

# Now SERIES is a list of dicts, with authors and genres as lists