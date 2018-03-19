import calendar
from datetime import datetime

import pytz


def dt_to_unix(dt):
    if isinstance(dt, datetime):
        dt = calendar.timegm(dt.utctimetuple())
    return dt


def unix_to_dt(dt):
    if isinstance(dt, (int, float)):
        dt = datetime.fromtimestamp(dt, pytz.utc)
    return dt
