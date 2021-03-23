from datetime import datetime as dt, time as dtt, timedelta as td
from ibapi.contract import Contract
from math import ceil
from pandas import DataFrame as DF, to_datetime as to_dt
from itertools import count
from pandas_market_calendars import get_calendar; nyse = get_calendar("NYSE")
from threading import Event
from collections import namedtuple

class Request_Manager:
    savefolder = r"C:\Users\User\Desktop\Python\TradeCode\TWS_SPY_Data\ignore"
    id = count(1)
    Reqs = {}
    COLS = ["Date", "Open", "High", "Low", "Close", "Volume"]
    IBDT = "%Y%m%d %H:%M:%S"
    Stamp = namedtuple("Stamp", ["req", "sym", "event"])

    ibtfs = dict(s= "sec", m= "min", h= "hour", D= "day", W= "W", M= "M")
    validibtfs = "1 secs, 5 secs, 10 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins, 20 mins," \
                 " 30 mins, 1 hour, 2 hours, 3 hours, 4 hours, 8 hours, 1 day, 1W, 1M".replace(", ", ",").split(",")

    tfratios = dict(s = td(seconds= 1), m= td(minutes= 1), h= td(hours=1),
                    D= td(days=1), W= td(weeks= 1))

    ratios = dict(s=td(seconds=1), m=td(minutes=1), h=td(hours=1),
                    D=td(minutes=60* 16), W=td(minutes=60*16*5), M=td(days=60*16*20))


    def __init__(self):
        self.threadwait = True
        self.directreturn = True


    @staticmethod
    def makeContract(symbol):
        contract = Contract()
        contract.symbol = symbol.upper().strip().replace('.', ' ').replace(',', ' ')
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"
        return contract

    def getHeadTimeStamp(self, symbol, type_= "TRADES", onlyRTH= False, format_= 1, transmit= None):
        if isinstance(symbol, str):
            contract = self.makeContract(symbol)
        else: contract, symbol = symbol, symbol.symbol

        # set the namedtuple with: request args, symbol, and Event to be waited for
        Req = Stamp([next(self.id), contract, type_, int(onlyRTH), format_], symbol, Event())
        self.Reqs[Req.req[0]] = Req # adding the namedtuple to class.Reqs with its unique id as key

        # the choice is between immediately transmitting and waiting for the response
        # or getting the request args as a list
        if transmit:
            Req.event.clear()
            transmit.reqHeadTimeStamp(*Req.req)
            Req.event.wait()
            if self.directreturn: return Req.req
        else: return Req.req

    def receiveStamp(self, id_, stamp):
        self.Reqs[id_].req= stamp
        self.Reqs[id_].event.set()

        if not self.directreturn:
            return stamp, self.Reqs[id_].sym
        else: return None, None

    def makeRequest(self, symbol, timeframe, start, end= None, format_= 1,
                    onlyRTH= False, type_= "TRADES", setDateasIndex= True, transmit= None):

        oneday= False
        if isinstance(symbol, str):
            contract = self.makeContract(symbol)
        else: contract, symbol = symbol, symbol.symbol

        start, end, nstart, nend = self._set_request_dates(start, end)
        tfdelta = self.ratios[timeframe[-1]]* int(timeframe[:-1])
        ndays, duration = self.date_duration(start, end)

        nrows = ceil(ndays* self.ratios["D"]/tfdelta)
        nreqs = (nrows//5000)+1
        timeframe = self._tf(timeframe)

        if nreqs== 1:
            theReq = Request(contract, timeframe,[(duration, self._ib(nend))], format_, int(onlyRTH), type_,
                           start, end, setDateasIndex= setDateasIndex, oneday= oneday, orig_sym= symbol)
        else:
            add = (nend - nstart)/ nreqs
            reqs = [nstart+add*i for i in range(nreqs)]

            duration_end = []
            for st in reqs:
                thisend = st+add
                ndays, duration = self.date_duration(st, thisend)
                duration_end.append((duration, self._ib(thisend)))

            theReq = Request(contract, timeframe, duration_end, format_, int(onlyRTH), type_,
                           start, end, setDateasIndex= setDateasIndex, oneday= oneday, orig_sym= symbol)

        if not transmit:
            return theReq
        else:
            for req in theReq.ToUnpack:
                if self.threadwait: theReq.EndEvent.clear()

                transmit.reqHistoricalData(*req)

                if self.threadwait and not theReq.EndEvent.wait(150):
                    transmit.historicalDataEnd(req[0], 0, "timed out")

            if self.directreturn:
                if theReq.data.shape[0]: return theReq.data
                else: return "No Data"
            # TODO: Check the implications of blocking and not directreturn when someone doesn't
            #  use their own event to make sure the response has arrived before continuing with the
            #  code after this.

    def _set_request_dates(self, start, end):
        if end is None:
            nstart = dt.combine(start.date(), dtt(0))
            end = nend = dt.combine(dt.now().date(), dtt(0)) +td(1)

        elif start == end:
            start = nstart = dt.combine(start.date(), dtt(0))
            end = nend = dt.combine(end.date(), dtt(0)) +td(1)

        else:
            nstart = dt.combine(start.date(), dtt(0))
            nend = dt.combine(end.date(), dtt(0)) +td(1)
            if end.time() == dtt(0):
                end = nend

        return start, end, nstart, nend


    def date_duration(self, start, end):
        ndays = nyse.schedule(start_date=start, end_date=end).index
        if not ndays.shape[0]: raise ValueError("\n\n --- > no tradingdays in that range")
        diff = ndays[-1]- ndays[0]
        ndays = ndays.shape[0]

        if ndays < 365: duration =  f"{ndays} D"
        else: duration = f"{diff//td(365)+ 1} Y"

        return ndays, duration

    def _tf(self, tf):
        x = int(tf[:-1])
        label = self.ibtfs[tf[-1]]

        if x == 1: label = f"{x} {label}"
        else: label = f"{x} {label}s"

        if not label in self.validibtfs:
            raise ValueError(f"only the following tfs are allowed:\n{self.validibtfs}")
        return label

    def _ib(self, dte): return dt.strftime(dte, self.IBDT)

    def _standardcsv(self, id_):
        sym, tf = self.Reqs[id_].contract.symbol, self.Reqs[id_].timeframe
        st, end = self._ib(self.Reqs[id_].start), self._ib(self.Reqs[id_].end)
        fn = f"{sym}_{tf}_{st}_{end}.csv".replace(":","").replace(" ","")
        return rf"{self.savefolder}\{fn}"

    def add(self, id_, bar):
        self.Reqs[id_].data.append(
        [bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def ishistdatareq(self, id_): return not isinstance(self.Reqs[id_], self.Stamp)

    def markasfailed(self, id_):
        self.Reqs[id_].Failed = True

    def end(self, id_, save= False):
        # increments the
        self.Reqs[id_].received += 1
        if self.Reqs[id_].received == self.Reqs[id_].nreqs:

            # this makes the dataframe, and sorts it
            self.Reqs[id_].data = DF(self.Reqs[id_].data, columns= self.COLS)
            self.Reqs[id_].data = self.Reqs[id_].data.sort_values("Date").drop_duplicates("Date")
            self.Reqs[id_].data["Date"] = to_dt(self.Reqs[id_].data["Date"], infer_datetime_format= True)

            # checking whether one day was requested to adjust the end cut off
            if self.Reqs[id_].end.time() == dtt(0) and not self.Reqs[id_].oneday:
                end = self.Reqs[id_].end + td(1)
            else: end = self.Reqs[id_].end

            # here the actually requested dates are used to trim the df and Date set to index
            mask = (self.Reqs[id_].start<= self.Reqs[id_].data["Date"])& (self.Reqs[id_].data["Date"]< end)
            self.Reqs[id_].data = self.Reqs[id_].data[mask]
            if self.Reqs[id_].setDateasIndex:
                self.Reqs[id_].data.set_index("Date", inplace= True)

            # possibly saved
            if save:
                if save is True:
                    self.Reqs[id_].data.to_csv(self._standardcsv(id_),
                                              index= self.Reqs[id_].setDateasIndex)
                elif save.endswith(".csv"):
                    self.Reqs[id_].data.to_csv(fr"{self.savefolder}\{save}",
                                              index= self.Reqs[id_].setDateasIndex)

            # either  nothing (directreturn) or return value in historicalDataEnd triggering self.response
            self.Reqs[id_].EndEvent.set()
            if not self.directreturn:
                if self.Reqs[id_].data.shape[0]:
                    return self.Reqs[id_].data
                else: return "No Data"

        else: self.Reqs[id_].EndEvent.set()

    def Req(self, id_): return self.Reqs[id_]

    def tf_sym(self, id_):
        if id_ in self.Reqs:
            if self.ishistdatareq(id_):
                return self.Reqs[id_].timeframe, self.Reqs[id_].orig_sym
            else:
                return "stamp", self.Reqs[id_].sym

        else: return "Not a used id", "Not a used id"



class Request:

    def __init__(self, contract, timeframe, duration_end, format_, onlyRTH,
                 type_, start, end, setDateasIndex= True, oneday= False, orig_sym= None):
        self.contract = contract
        self.timeframe = timeframe
        self.duration_end = duration_end
        self.format_= format_
        self.onlyRTH = onlyRTH
        self.type_ = type_

        self.oneday = oneday
        self.orig_sym = orig_sym or contract.symbol
        self.start, self.end = start, end
        self.ToUnpack, self.data = [], []
        self.EndEvent = Event()

        for duration, end in duration_end:
            id_ = next(Request_Manager.id)
            self.ToUnpack.append([id_, contract, end, duration, timeframe,
                          type_, onlyRTH, format_, False, []])
            Request_Manager.Reqs[id_] = self

        self.nreqs, self.received = len(self.ToUnpack), 0
        self.setDateasIndex = setDateasIndex
        self.Failed = False



class Stamp:

    def __init__(self, req, sym, event):
        self.req = req
        self.sym = sym
        self.event = event

class Response:

    def



