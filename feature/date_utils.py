from datetime import datetime, timedelta, date
from typing import Union, List

DateType = Union[str, datetime, date]

def to_date(date_input: DateType) -> date:
    """Converts input to a `date` object."""
    if isinstance(date_input, str):
        return datetime.strptime(date_input, "%Y-%m-%d").date()
    elif isinstance(date_input, datetime):
        return date_input.date()
    elif isinstance(date_input, date):
        return date_input
    else:
        raise ValueError("Unsupported date format. Use 'YYYY-MM-DD', datetime, or date object.")

def get_last_training_date(target_date: DateType, frequency: str = 'daily') -> date:
    """
    Returns the most recent training date on or before the target date based on frequency.
    """
    target_date = to_date(target_date)

    if frequency == 'daily':
        return target_date
    elif frequency == 'weekly':
        return target_date - timedelta(days=target_date.weekday())  # Last Monday
    elif frequency == 'monthly':
        return target_date.replace(day=1)
    else:
        raise ValueError("Invalid frequency. Use 'daily', 'weekly', or 'monthly'.")

def get_training_dates(
    target_date: DateType,
    lookback_days: int,
    lag: int = 3,
    frequency: str = 'daily'
) -> List[date]:
    """
    Returns a list of training dates within the lookback window.
    - `target_date`: the reference date
    - `lookback_days`: how many days to go back from `target_date`
    - `lag`: how many days before `target_date` to end the training data
    - `frequency`: 'daily', 'weekly', or 'monthly'
    """
    target_date = to_date(target_date)
    end_date = target_date - timedelta(days=lag)
    start_date = target_date - timedelta(days=lookback_days)

    training_dates = []
    current = start_date

    while current <= end_date:
        if frequency == 'daily':
            training_dates.append(current)
        elif frequency == 'weekly' and current.weekday() == 0:  # Monday
            training_dates.append(current)
        elif frequency == 'monthly' and current.day == 1:
            training_dates.append(current)
        current += timedelta(days=1)

    return training_dates
