
MIN_VALUE = -32
MAX_VALUE = 95


def dbz_to_precipitation_rate(dbz: float, a: float = 200, b: float = 1.6):
    """
    Converts radar reflectivity to mm/h

    Parameters
    ----------
    dbz : float
        dBZ value
    a : float
        Parameter a of the Z/R relationship Standard value according to Marshall-Palmer is a=200
    b : float
        Parameter b of the Z/R relationship Standard value according to Marshall-Palmer is b=1.6
    """
    decib = 10.0 ** (dbz / 10.0)
    return (decib / a) ** (1.0 / b)
