# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from babel.dates import DateTimePattern, parse_pattern


def babel2datetime(pattern):
    """Convert date format from babel
    (http://babel.pocoo.org/docs/dates/#date-fields)) to a format understood by
    datetime.strptime.
    """
    if not isinstance(pattern, DateTimePattern):
        pattern = parse_pattern(pattern)

    map_fmt = {
        # days
        'd': '%d',
        'dd': '%d',
        'EEE': '%a',
        'EEEE': '%A',
        'EEEEE': '%a',  # narrow name => short name
        # months
        'M': '%m',
        'MM': '%m',
        'MMM': '%b',
        'MMMM': '%B',
        # years
        'y': '%Y',
        'yy': '%Y',
        'yyyy': '%Y',
        # hours
        'h': '%I',
        'hh': '%I',
        'H': '%H',
        'HH': '%H',
        # minutes,
        'm': '%M',
        'mm': '%M',
        # seconds
        's': '%S',
        'ss': '%S',
        # am/pm
        'a': '%p',
    }

    return pattern.format % map_fmt
