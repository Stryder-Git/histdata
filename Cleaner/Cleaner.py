from Cleaner.Analyzer import Analyzer
from Cleaner.mylogging import MissingDates

from numpy import append, timedelta64, split, delete, argwhere, setdiff1d
from pandas import concat
from datetime import datetime as dt, time as dtt, date as ddt
from time import sleep
from itertools import count


class Cleaner(Analyzer):

    def __init__(self, HistData= None, clientid= None):
        Analyzer.__init__(self)
        if HistData is None: # if no existing instance passed, import and create
            if clientid is None: # then a clientid will be necessary
                raise ValueError("clientid must be specified")
            from HistData import HistData
            self.hd = HistData(clientid)

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
        tofill = self.DatesToFill(data)
        self.missingdates.info(f"{data.sym}:\n{tofill}")
        self.datatoconcat[data.sym] = []
        if not tofill:
            self.validsymbol = False
            print("\nnothing to fill: ", len(tofill), "\n")
            return data

        nreqs = len(tofill); updlst =[]
        for nupd, dates in enumerate(tofill):
            if not self.validsymbol: return data
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



