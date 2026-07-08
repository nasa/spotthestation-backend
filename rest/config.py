import os


def calculate_data_on_boot():
    return os.getenv('CALCULATE_DATA_ON_BOOT', '').strip().lower() in ('1', 'true', 'yes', 'on')
