def add_hyphens_to_uuid(uuid_string):
    formatted_uuid = '-'.join([uuid_string[i:i+4] for i in range(0, len(uuid_string), 4)])
    return formatted_uuid
