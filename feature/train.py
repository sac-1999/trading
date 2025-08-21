import date_utils
from datetime import datetime
import pandas as pd
start_date = datetime.today(2025, 5, 1)
end_date = datetime.today(2025, 7, 21)
freq = "15min"
model_train_freq = "weekly"
train_lookback_days = 63
training_dates = date_utils.get_training_dates(target_date, train_lookback_days, lag=1, frequency=model_train_freq)


def dataset(end_date, lookback_days):
    