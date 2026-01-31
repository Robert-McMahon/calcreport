import csv
from bs4 import BeautifulSoup

# Sample HTML content (replace this with your actual HTML content)
with open('calcreport/calcreport/export/tire_data.html', 'r') as file:
    html_content = file.read()

# Parse the HTML content
soup = BeautifulSoup(html_content, 'html.parser')

# Find all option elements
options = soup.find_all('option')

# Define the CSV file header
header = [
    'size', 'loadrange', 'speedrating', 'treaddepth', 'servicedesc',
    'sidewallstyling', 'articlenumber', 'rimwidth', 'tirediameter',
    'tireweight', 'currency', 'msrp', 'warrantydistance', 'warrantyunits', 'articles'
]

# Open a CSV file for writing
with open('tire_data.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)  # Write the header

    # Write the data for each option element
    for option in options:
        row = [
            option.get('data-size'),
            option.get('data-loadrange'),
            option.get('data-speedrating'),
            option.get('data-treaddepth'),
            option.get('data-servicedesc'),
            option.get('data-sidewallstyling'),
            option.get('data-articlenumber'),
            option.get('data-rimwidth'),
            option.get('data-tirediameter'),
            option.get('data-tireweight'),
            option.get('data-currency'),
            option.get('data-msrp'),
            option.get('data-warrantydistance'),
            option.get('data-warrantyunits'),
            option.get('data-articles')
        ]
        writer.writerow(row)

print("CSV file 'tire_data.csv' has been created.")