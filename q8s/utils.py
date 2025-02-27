def extract_non_none_value(arr):
    non_none_values = [x for x in arr if x is not None]
    return non_none_values[0] if non_none_values else None
