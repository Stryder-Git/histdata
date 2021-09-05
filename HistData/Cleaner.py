from .mylogging import MissingDates

from numpy import append, timedelta64, split, delete, argwhere, setdiff1d, unique
from pandas import concat, to_datetime
from pandas_market_calendars import get_calendar
from datetime import datetime as dt, date as ddt, time as dtt
from time import sleep
from itertools import count
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




class Cleaner(Analyzer):

    def __init__(self, HistData= None, clientid= None):
        Analyzer.__init__(self)
        if HistData is None: # if no existing instance passed, import and create
            if clientid is None: # then a clientid will be necessary
                raise ValueError("clientid must be specified")
            from HistData import HistData
            self.hd = HistData(clientid)
            self.hd.Blocking(True)

        else: self.hd = HistData
        if not self.hd.Block: raise ValueError("HistData instance must be blocking")
        self.datatoconcat = {}
        self.missingdates = MissingDates
        self.nmissingandincomplete = {}
        self.validsymbol = True

    def DatesToFill(self, data) -> list:
        """ creates a list of lists, containing a start and end date
        for the ranges of dates that need to be filled"""
        missing = self.getmissingDays(data)
        incomplete = self.getincompleteDays(data)
        if missing.shape[0] or incomplete.shape[0]:
            arr =  append(missing, incomplete)
            self.logprintmissingincomplete("before", missing, incomplete, data.sym)

            # ixs are indexes of dates that are more than one day away from the next
            # which will be used to split the arr
            arr.sort()
            lastix, oneday = arr.shape[0]-1, timedelta64(1, "D")
            ixs = argwhere((arr[1:] - arr[:-1]) > oneday).flatten()
            oddones, ix_to_remove = [], []
            for i in ixs:
                if not i:
                    oddones.append(arr[i])
                    ix_to_remove.append(i)
                    continue
                i += 1
                if i == lastix:
                    oddones.append(arr[i])
                    ix_to_remove.append(i)
                else:
                    if arr[i + 1] - arr[i] > oneday:
                        oddones.append(arr[i])
                        ix_to_remove.append(i)

            arr = delete(arr, ix_to_remove)
            ixs = argwhere((arr[1:] - arr[:-1]) > oneday).flatten()
            if arr.shape[0]:
                ranges = [sub[[0, -1]].tolist() for sub in split(arr, ixs + 1)]
            else: ranges = []
            ranges.extend([[odd] * 2 for odd in oddones])

        else: ranges = []
        return ranges

    def _conv(self, start, end):
        if not isinstance(start, ddt): start = start.astype(dt)
        if not isinstance(end, ddt): end = end.astype(dt)

        start = dt.combine(start, dtt(0))
        end = dt.combine(end, dtt(0))
        return start, end

    def getData(self, data, tf, start, end):
        """ the data will be requested and checked for errors then the same will be requested
        three more times or until there are no more errors. Then the data will be added."""

        resp = self.hd.get(data.sym, tf, start, end)
        att = count(0)
        while not resp and next(att) < 2:
            if "invalid symbol" in resp.errors:
                self.validsymbol = False
                self.missingdates.info(f"{data.sym}: INVALID SYMBOL")
                print(f"{data.sym}: INVALID SYMBOL")
                break

            print(resp.errors, " ", start, end)
            sleep(10)
            resp = self.hd.get(data.sym, tf, start, end)

        if self.validsymbol and resp:
            self.datatoconcat[data.sym].append(resp.data)

    def FillMissingData(self, data):
        """ the main method, which will get the dates to fill, and then start looping
        over the dateranges. After the first loop, it will check if there are any new missing,
        incomplete dates and then request those again."""
        self.validsymbol = True
        original_clean = self.hd.ImmediatelyCleanData
        self.hd.setImmediatelyCleanTo(False)

        tofill = self.DatesToFill(data)
        self.missingdates.info(f"{data.sym}:\n{tofill}")
        self.datatoconcat[data.sym] = []
        if not tofill:
            self.validsymbol = False
            print("\nnothing to fill: ", len(tofill), "\n")
            self.hd.setImmediatelyCleanTo(original_clean)
            return data

        nreqs = len(tofill); updlst =[]
        for nupd, dates in enumerate(tofill):
            if not self.validsymbol:
                self.hd.setImmediatelyCleanTo(original_clean)
                return data
            self.getData(data, "1m", *self._conv(*dates))

            if upd := ((nupd + 1) / nreqs // .1):
                upd = int(upd * .1 * 100)
                if upd not in updlst: print(f"{upd}% done");  updlst.append(upd)

        newdf, missing, incomplete = self.concatandcheck(data.df, data.sym, "after")
        # to find the ones that weren't missing or incomplete before
        diff_incompl = setdiff1d(incomplete, self.getincompleteDays(data))
        diff_missing = setdiff1d(missing, self.getmissingDays(data))

        if diff_missing.shape[0] or diff_incompl.shape[0]:
            issues = [*diff_missing.tolist(), *diff_incompl.tolist()]
            print("fixing issues")
            self.logprintnewlymissingincomplete(diff_missing, diff_incompl, issues, data.sym)

            for d in issues: self.getData(data, "1m", *self._conv(d, d))

            newdf = self.concatandcheck(newdf, data.sym, "now")[0]

        self.hd.setImmediatelyCleanTo(original_clean)
        return data._replace(df = newdf)

    def concatandcheck(self, df, sym, stage):
        df = concat([df, *self.datatoconcat[sym]])
        df = df[~df.index.duplicated()].sort_index()
        missing, incomplete = self.missingandincomplete(df)
        self.logprintmissingincomplete(stage, missing, incomplete, sym)
        return df, missing, incomplete

    def logprintmissingincomplete(self, stage, missing, incomplete, sym):
        print(f"missing {stage}: ", missing.shape[0], "\n",
              f"incompl {stage}: ", incomplete.shape[0])
        midct = dict(missinng=missing.shape[0], incomplete=incomplete.shape[0])
        self.missingdates.info(f"{sym} now: {midct}")
    def logprintnewlymissingincomplete(self, diff_missing, diff_incompl, issues, sym):
        newly_msg = f"\nnewly missing: \n{diff_missing}\n" \
                    f"newly incomplete: \n{diff_incompl}"
        print(newly_msg)
        self.missingdates.info(f"{sym}:\n{issues}")
        self.missingdates.info(f"{sym}:\n{newly_msg}")


    def clear_cache(self, data):
        self._cleardates_counts(data)
        del self.datatoconcat[data.sym]


