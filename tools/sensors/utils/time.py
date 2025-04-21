from datetime import datetime, timezone


class Timestamp:

    @staticmethod
    def get_current() -> int:
        return int(datetime.now(timezone.utc).timestamp())

    @staticmethod
    def floor(timestamp: int, period: int) -> int:
        """Align timestamp to closest and lower value that is dividable by period

        Parameters
        ----------
        timestamp : int
            Timestamp to floor
        period : int
            Period to align time
        """
        return timestamp - (timestamp % period)


def time_to_next_run(frequency):
    """
    Calculate the time to the next run of a task.

    Parameters
    ----------
    frequency : int
        The frequency of the task in seconds.

    Returns
    -------
    int
        The time to the next run of the task in seconds.
    """
    return frequency - Timestamp.get_current() % frequency
