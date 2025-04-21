import datetime


def floor_timestamp(timestamp: int, period: int) -> int:
    """Floors time to specified period

    Parameters
    ----------
    timestamp : int
        Timestamp to floor
    period : int
        Floor period

    Returns
    -------
    int
        Floored timestamp
    """
    return (timestamp - (timestamp % period))


def format_time(timestamp) -> str:
    utc_datetime = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
    return utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
