import pandas as pd
import random

counties = [
    'Nairobi', 'Mombasa', 'Kiambu', 'Nakuru', 'Kisumu', 'Machakos', 'Eldoret', 'Kakamega',
    'Meru', 'Nyeri', 'Thika', 'Garissa', 'Isiolo', 'Kericho', 'Bomet'
]
property_types = ['House', 'Apartment', 'Villa', 'Townhouse', 'Bungalow']

def generate_mock_property_data(n=100):
    data = []
    for _ in range(n):
        bedrooms = random.randint(1, 6)
        bathrooms = random.randint(1, 5)
        size_sqft = random.randint(500, 4500)
        location = random.choice(counties)
        property_type = random.choice(property_types)

        location_multiplier = {
            'Nairobi': 9000, 'Mombasa': 8500, 'Kiambu': 8000, 'Nakuru': 7500, 'Kisumu': 7000,
            'Machakos': 6800, 'Eldoret': 6500, 'Kakamega': 6200, 'Meru': 6000, 'Nyeri': 5800,
            'Thika': 5500, 'Garissa': 5000, 'Isiolo': 4800, 'Kericho': 4600, 'Bomet': 4400
        }
        base_price = location_multiplier[location] * size_sqft
        price = base_price + (bedrooms * 200000) + (bathrooms * 100000)

        data.append({
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'size_sqft': size_sqft,
            'location': location,
            'property_type': property_type,
            'price': int(price)
        })

    return pd.DataFrame(data)

# Generate and save
df = generate_mock_property_data(100)
df.to_csv("mock_property_data.csv", index=False)
print("mock_property_data.csv created successfully.")
