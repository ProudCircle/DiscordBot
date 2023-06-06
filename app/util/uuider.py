def add_hyphens_to_uuid(uuid_string):
    formatted_uuid = '{}-{}-{}-{}-{}'.format(
        uuid_string[:8],
        uuid_string[8:12],
        uuid_string[12:16],
        uuid_string[16:20],
        uuid_string[20:]
    )
    return formatted_uuid
