#
# Field filters
#
def strip(data):
    """
    Strip data if data is a string
    """
    if not isinstance(data, basestring):
        return data
    return data.strip()


def uppercase(data):
    if not isinstance(data, basestring):
        return data
    return data.upper()

