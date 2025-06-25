# Configuration for column mappings and store info

# VAUTO column mappings for USED inventory (update as needed)
VAUTO_COLUMNS_USED = {
    'stock_number': 'Stock #',  # Updated to match actual VAUTO file column
    'vin': 'VIN',
    'store': 'Dealer Name',
    # Add or update other fields as needed
}

# VAUTO column mappings for NEW inventory (update as needed)
VAUTO_COLUMNS_NEW = {
    'stock_number': 'Stock #',
    'vin': 'VIN',
    'status': 'Status',
    'store': 'Dealer Name',  # This is your store column
    # Add more fields as needed
}

# Reynolds column mappings
REYNOLDS_COLUMNS = {
    'stock_number': 'Stock #',
    'year': 'Year',
    'make': 'Make',
    'model': 'Model',
    'status': 'Status',
    'store': 'Lot Location',
    'type': 'N/U',      # 'New' or 'Used'
}

# Reynolds column mappings for NEW inventory (add or update as needed)
# NOTE: Matching will be only by stock number, as VIN is not present in the file
REYNOLDS_COLUMNS_NEW = {
    'stock_number': 'Stock #',
    'status': 'Status',
    # Add more fields as needed
}

# List of stores (update as needed)
STORES = [
    'Store 1', 'Store 2', 'Store 3', 'Store 4', 'Store 5', 'Store 6'
]

# For NEW inventory, update VAUTO_COLUMNS_NEW if the structure differs.

# Reynolds column mappings for USED inventory (if needed)
REYNOLDS_COLUMNS = {
    'stock_number': 'Stock #',
    'status': 'Status',
    # Add more fields as needed
}
# Matching for Reynolds is only by stock number since VIN is not present.

# For USED inventory, update VAUTO_COLUMNS_USED as needed.