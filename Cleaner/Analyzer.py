from pandas_market_calendars import get_calendar
from numpy import unique
from pandas import to_datetime
from datetime import time as dtt
from collections import namedtuple


class Analyzer:
    tradingdays = get_calendar("NYSE").schedule
    nbars = 390
    opent, closet = dtt(9,30), dtt(15,59)
    Data = namedtuple("Data", ["sym", "df"])

    def __init__(self):
        self.dates_counts = {}

    def nyse(self, start, end): return self.tradingdays(start, end).index

    def _cleardates_counts(self, data): del self.dates_counts[data.sym]

    def _getdates_counts(self, data):
        if not data.sym in self.dates_counts:
            dates, counts = unique(
                data.df.loc[self.opent: self.closet].index.date, return_counts= True)
            self.dates_counts[data.sym] = dates.astype("datetime64[D]"), counts
        else:
            dates, counts = self.dates_counts[data.sym]
        return dates, counts

    def Form(self, sym, df): return self.Data(sym, df)

    def Prepare(self, data, df= None):
        if not df is None: data = self.Form(data, df)
        if "Date" in data.df.columns:
            data.df["Date"] = to_datetime(data.df["Date"], infer_datetime_format= True)
            df = data.df.drop_duplicates("Date").set_index("Date").sort_index()
        else:
            df = data.df[~data.df.index.duplicated()].sort_index()
        data = data._replace(df= df)
        _ , _ = self._getdates_counts(data)
        return data

    def getmissingDays(self,data):
        dates = self._getdates_counts(data)[0]
        first, last = data.df.iloc[[0,-1]].index
        tradingdays = self.nyse(first, last)
        missing = tradingdays[~tradingdays.isin(dates)]
        return missing.values.astype("datetime64[D]")

    def getincompleteDays(self, data):
        dates, counts = self._getdates_counts(data)
        return dates[counts!=self.nbars]

    def missingandincomplete(self, df):
        checkdf = df.loc[self.opent:self.closet]
        dates, counts = unique(checkdf.index.date, return_counts= True)
        first, last = checkdf.iloc[[0,-1]].index
        tradingdays = self.nyse(first, last)

        missing = tradingdays[~tradingdays.isin(dates)]
        incomplete = dates[counts!=self.nbars]
        return missing.values.astype("datetime64[D]"), incomplete

