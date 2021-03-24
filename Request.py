from datetime import datetime as dt, time as dtt, timedelta as td
from ibapi.contract import Contract
from math import ceil
from pandas import DataFrame as DF, to_datetime as to_dt
from itertools import count
from pandas_market_calendars import get_calendar; nyse = get_calendar("NYSE")
from threading import Event
from time import time


class Request_Maker:
    """ holds variables and methods needed to set up the requests"""

    savefolder = r"C:\Users\User\Desktop\Python\TradeCode\TWS_SPY_Data\ignore"
    id = count(1)
    COLS = ["Date", "Open", "High", "Low", "Close", "Volume"]
    IBDT = "%Y%m%d %H:%M:%S"
    TIMEOUT = 150
    ibtfs = dict(s= "sec", m= "min", h= "hour", D= "day", W= "W", M= "M")
    validibtfs = "1 secs, 5 secs, 10 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins, 20 mins," \
                 " 30 mins, 1 hour, 2 hours, 3 hours, 4 hours, 8 hours, 1 day, 1W, 1M".replace(", ", ",").split(",")

    tfratios = dict(s = td(seconds= 1), m= td(minutes= 1), h= td(hours=1),
                    D= td(days=1), W= td(weeks= 1))

    ratios = dict(s=td(seconds=1), m=td(minutes=1), h=td(hours=1),
                    D=td(minutes=60* 16), W=td(minutes=60*16*5), M=td(days=60*16*20))

    @staticmethod
    def makeContract(symbol):
        if isinstance(symbol, Contract): return symbol, symbol.symbol

        contract = Contract()
        contract.symbol = symbol.upper().strip().replace('.', ' ').replace(',', ' ')
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"
        return contract, symbol

    def set_request_dates(self, start, end):
        if start == end:
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

    def calc_nreqs(self, tf, ndays):

        tfdelta = self.ratios[tf[-1]]* int(tf[:-1])
        nrows = ceil(ndays* self.ratios["D"]/tfdelta)
        return  (nrows//5000)+1


    def _tf(self, tf):
        x = int(tf[:-1])
        label = self.ibtfs[tf[-1]]

        if x == 1: label = f"{x} {label}"
        else: label = f"{x} {label}s"

        if not label in self.validibtfs:
            raise ValueError(f"only the following tfs are allowed:\n{self.validibtfs}")
        return label

    def _ib(self, dte): return dt.strftime(dte, self.IBDT)



class Request_Manager(Request_Maker):
    Reqs = {}

    def __init__(self):
        self.threadwait = True
        self.directreturn = True

    def getHeadTimeStamp(self, symbol, type_= "TRADES", onlyRTH= False, format_= 1, transmit= None):
        contract, symbol = self.makeContract(symbol)

        # set the Stamp with: request args, symbol, and Event to be waited for
        Req = Stamp([next(self.id), contract, type_, int(onlyRTH), format_], symbol, Event())
        self.Reqs[Req.req[0]] = Req # adding the Stamp to class.Reqs with its unique id as key

        # the choice is between immediately transmitting and waiting for the response
        # or getting the request args as a list
        if transmit:
            if self.threadwait: Req.event.clear()

            transmit.reqHeadTimeStamp(*Req.req)
            if self.threadwait:
                Req.event.wait()
                if self.directreturn: return Req.req


        else: return Req

    def receiveStamp(self, id_, stamp):
        self.Reqs[id_].req = stamp
        self.Reqs[id_].event.set()

        if not self.directreturn:
            return stamp, self.Reqs[id_].sym
        else: return None, None


    def makeRequest(self, symbol, timeframe, start, end, format_= 1,
                    onlyRTH= False, type_= "TRADES", setDateasIndex= True, transmit= None):
        """ main access point of this Module"""

        contract, symbol = self.makeContract(symbol)
        start, end, nstart, nend = self.set_request_dates(start, end) # nend and nstart are for the request
        ndays, duration = self.date_duration(start, end) # the duration for IB format
        nreqs = self.calc_nreqs(timeframe, ndays) # necessary number of reqs

        # create the combination of duration and enddate for each ib request
        add, duration_end = (nend - nstart)/ nreqs, []
        for i in range(nreqs):
            thisstart = nstart+add*i; thisend = thisstart + add
            duration_end.append(
                (self.date_duration(thisstart, thisend)[1], self._ib(thisend)))

        # make the Request object
        theReq = Request(contract, self._tf(timeframe), duration_end, format_, int(onlyRTH),
                         type_, start, end, setDateasIndex= setDateasIndex, orig_sym= symbol)

        if transmit:
            return theReq.transmit_requests(transmit, self.threadwait, self.directreturn)

        else: return theReq


    def add(self, id_, bar): self[id_].addBar(bar)

    def ishistdatareq(self, id_): return not isinstance(self.Reqs[id_], Stamp)

    def end(self, id_, err): return self[id_].setEnd(id_, err)

    def tf_sym(self, id_):
        try: return self[id_].timeframe, self[id_].orig_sym
        except KeyError: return "Not a used id", "Not a used id"

    def clear(self): self.Reqs.clear()

    def __getitem__(self, id_): return self.Reqs[id_]



class Request:

    def __init__(self, contract, timeframe, duration_end, format_, onlyRTH,
                 type_, start, end, setDateasIndex= True, orig_sym= None):
        self.contract = contract
        self.timeframe = timeframe
        self.orig_sym = orig_sym or contract.symbol

        self.start, self.end = start, end
        self.ToUnpack, self.ixlink, self.data = {}, [], []
        self.EndEvent = Event()

        for duration, end in duration_end:
            id_ = next(Request_Manager.id)
            self.ToUnpack[id_] = IBRequest([id_, contract, end, duration, timeframe,
                          type_, onlyRTH, format_, False, []])
            self.ixlink.append(id_)
            Request_Manager.Reqs[id_] = self

        self.nreqs, self.received = len(self.ToUnpack), 0
        self.setDateasIndex = setDateasIndex
        self.Response = Response(orig_sym, timeframe)
        self.directreturn = True
        self.current = -1

    def transmit_requests(self, transmitter, wait= True, direct= True):
        """ loops over the IBRequests, possibly waiting and timing them"""
        self.directreturn = direct
        for id_, req in self:
            if wait: self.EndEvent.clear()
            req.t_requested = time()
            transmitter.reqHistoricalData(*req)

            if wait and not self.EndEvent.wait(Request_Manager.TIMEOUT):
                self.setEnd(id_, "timed out")

        if wait and direct: return self.Response

    def addBar(self, bar):
        """ appends the pricedata row as a list to the list of lists in Req.data"""
        self.data.append(
        [bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def setEnd(self, id_, err):
        """ this method finalizes a transmitted request by taking the speed,
        incrementing the received number, and saving potential errors.
        If the last of the required requests has been reached, the df is made
        and the Reponse object finished"""

        self[id_].speed = time() - self[id_].t_requested
        self.received += 1
        self.Response._updspeed(self[id_].speed, self.received)
        if err: self[id_].error = err; self.Response.nerrors += 1

        if self.received == self.nreqs:
            # this makes the dataframe, sorts it, drops duplicates and trims it
            self.data = DF(self.data, columns=Request_Manager.COLS)
            self.data["Date"] = to_dt(self.data["Date"], infer_datetime_format=True)
            self.data = self.data.sort_values("Date").drop_duplicates("Date")
            # if a date (no time) was requested, adjust the end cut off to include the whole day
            if self.end.time() == dtt(0): end = self.end + td(1)
            else: end = self.end
            # trim it
            mask = (self.start <= self.data["Date"]) & (self.data["Date"] < end)
            self.data = self.data[mask]
            if self.setDateasIndex: self.data.set_index("Date", inplace=True)

            # finish the response object
            self.Response.finalize(self.data, [self[i] for i in self.ixlink])
            self.EndEvent.set()
            # make it return None when directreturn is desired
            if not self.directreturn: return self.Response

        else: self.EndEvent.set()


    def __getitem__(self, id_): return self.ToUnpack[id_]
    def __iter__(self): return self
    def __next__(self):
        self.current += 1
        if self.current == self.nreqs: raise StopIteration
        id_ = self.ixlink[self.current]
        return self.ToUnpack[id_].id_, self.ToUnpack[id_]


class IBRequest:
    """ only used to keep track of speed/errors for each request made to IB"""

    def __init__(self, req):
        self.req, self.id_ = req, req[0]
        self.t_requested = self.speed = self.error = None

    def __iter__(self): return iter(self.req)
    def __repr__(self): return self.req

class Stamp:
    def __init__(self, req, sym, event):
        self.req = req
        self.orig_sym = sym
        self.sym = sym
        self.event = event
        self.timeframe = "stamp"


class Response:
    """ This is the object that will be returned either directly by
    calling the Manager's getHistData method or through the overwritten
    response method"""

    def __init__(self, sym, tf):
        self.sym = sym
        self.tf = tf
        self.data = DF
        self.nerrors = self.speed = self.nreqs = 0
        self.requests, self.errors, self.success = [], [], False

    def _updspeed(self, speed, n): self.speed= (self.speed*(n-1)+ speed)/n

    def finalize(self, data, reqs):
        """ saves the returned data and sets the success attribute
        if a dataframe was returned, it's considered a success
        if not then its only a success if there are less errors than
        requests"""

        self.data = data
        self.requests = reqs
        self.nreqs = len(reqs)
        if isinstance(data, DF) and data.shape[0]: self.success = True
        else: self.success = self.nerrors < self.nreqs
        if self.nerrors:
            self.errors = self.return_errors(drop_duplicates= False)


    def __bool__(self):
        return self.success

    def return_errors(self, withid= False, drop_duplicates= True):
        if not withid:
            errs = [r.error for r in self.requests if not r.error is None]
            return list(set(errs)) if drop_duplicates else errs
        else: return [(r.id_, r.error) for r in self.requests]

    def return_speeds(self, withid= False):
        if not withid: return [r.speed for r in self.requests]
        else: return [(r.id_, r.speed) for r in self.requests]



