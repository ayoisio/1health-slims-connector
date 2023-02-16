#! python
import pytz
from dateutil.parser import parse as dtparse
from pytz import timezone


def make_utc_from_string(string_date, tz=None):
    """
    Convert string to UTC datetime
    """
    date = dtparse(string_date)
    if tz is not None:
        if date.tzinfo is not None:
            date = date.astimezone(timezone(tz)).replace(tzinfo=None)
        return timezone(tz).localize(date).astimezone(pytz.UTC)
    return date.astimezone(pytz.UTC)

