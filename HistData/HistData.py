from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract


from threading import Thread, Event
import logging
logger = logging.getLogger(__name__)

from math import ceil
import datetime as dt
import pandas as pd
import pandas_market_calendars as mcal
from itertools import count

from time import time

NYSE = mcal.get_calendar("NYSE")
FOURDAYS = pd.Timedelta("4D")
WEEK = pd.Timedelta("7D")

class HistData(EWrapper, EClient):
    logger = logger
    ErrResponses = ["No Data", "invalid symbol", "No head time stamp", "timed out"]
    Reqs = {}
    BLACKLIST = []
    TIMEOUT = 300
    DEF_CLIENTID = 9999
    DEF_PORT = 7497
    DEF_IP = '127.0.0.1'

    def __init__(self, ip= None, clientid= None, port= None):
        if clientid is None: clientid = self.DEF_CLIENTID
        if port is None: port = self.DEF_PORT
        if ip is None: ip = self.DEF_IP

        EClient.__init__(self, self)
        self.connect(ip, port, clientid)
        Thread(target= self.run, daemon= True).start()
        self.Block = True
        self.IBTWSConnected = False
        self._threadwait = True
        self.directreturn = True
        self.today = pd.Timestamp("now").normalize()

    def nextValidId(self, id_):
        self.logger.info("connected nextValidId: %s", id_)
        self.IBTWSConnected = True

    def _log_error(self, level, id_, code, string, prefix= ""):
        self.logger.log(level, "%s%s: %s - %s", prefix, id_, code, string)

    def error(self, id_, code, string):
        if id_ == -1:
            if "Connectivity between IB and Trader Workstation has been lost" in string:
                self._log_error(logging.CRITICAL, id_, code, string, prefix= "INTERNET DOWN --- ")
                self.IBTWSConnected = False
            elif "Connectivity between IB and Trader Workstation has been restored" in string:
                self._log_error(logging.CRITICAL, id_, code, string, prefix= "INTERNET BACK --- ")
                self.IBTWSConnected = True
            else:
                self._log_error(logging.DEBUG, id_, code, string, prefix= "UNCAUGHT --- ")

        if "query returned no data" in string:
            self._log_error(logging.DEBUG, id_, code, string)
            self.historicalDataEnd(id_, code, "No Data")

        elif "No head time stamp" in string:
            self._log_error(logging.DEBUG, id_, code, string)
            self.headTimestamp(id_, "No head time stamp")

        elif "No security definition" in string or "is ambiguous" in string:
            self._log_error(logging.WARNING, id_, code, string)
            if not self.IBTWSConnected: return
            if self.ishistdatareq(id_): self.historicalDataEnd(id_, code, "invalid symbol")
            else: self.headTimestamp(id_, "invalid symbol")

        elif "Request Timed Out" in string:
            self._log_error(logging.WARNING, id_, code, string)
            if self.ishistdatareq(id_): self.historicalDataEnd(id_, code, "timed out")
            else: self.headTimestamp(id_, "timed out")

        elif "Couldn't connect to TWS" in string or "Not connected" in string:
            self._log_error(logging.ERROR, id_, code, string)
            exit()
        else:
            self._log_error(logging.DEBUG, id_, code, string, prefix="UNCAUGHT --- ")

    @classmethod
    def setTimeOut(cls, seconds): cls.TIMEOUT = seconds

    @staticmethod
    def isResponse(obj): return isinstance(obj, Response)

    def isError(self, err_msg): return err_msg in self.ErrResponses

    def _transmit_request(self, request):
        func = self.reqHistoricalData if request.timeframe != "stamp" else self.reqHeadTimeStamp

        for req in request:
            self.Reqs[req.id] = request

            if self._threadwait: request.event.clear()
            self.logger.debug("SENDING REQUEST --- %s", req)
            func(*req)
            if self._threadwait and not request.event.wait(self.TIMEOUT):
                self.logger.info("EVENT TIMEOUT --- request id: %s", req.id)
                self.BLACKLIST.append(req.id)
                if isinstance(request, Stamp):
                    request.setEnd("timed_out")
                else:
                    request.setEnd(req.id, "timed out")

        if self._threadwait and self.directreturn:
            return request.Response

    def transmit_request(self, request):
        if self.Block:
            return self._transmit_request(request)
        else:
            Thread(target=self._transmit_request, args=request).start()

    def getHead(self, symbol, type_= "TRADES", onlyRTH= False, format_= 1):
        # set the Stamp with: request args, symbol, and Event to be waited for
        request = Stamp(symbol, type_, onlyRTH, format_)
        return self.transmit_request(request)

    def _cleandate(self, d):
        if isinstance(d, str):
            return dt.datetime.strptime(d, "%Y-%m-%d")
        else: return d

    def get(self, symbol, timeframe, start, end, format_=1, onlyRTH=False, type_="TRADES"):
        start, end = self._cleandate(start), self._cleandate(end)
        request = Request(symbol, timeframe, start, end, format_, onlyRTH, type_)
        return self.transmit_request(request)

    def ishistdatareq(self, id_): return not isinstance(self.Reqs[id_], Stamp)

    def _blacklist(self, id_):
        if id_ in self.BLACKLIST:
            self.logger.info(f"{self[id_].symbol}: {self[id_].orig_tf} @{self[id_][id_].t_requested}\n"
                               f"request: {self[id_][id_].req}\n"
                               f"was received after {time() - self[id_][id_].t_requested}s but TIMEOUT was {self.TIMEOUT}")
            return True

        return False

    def _calc_midpoint(self, left, right):

        """ calcs calendar day between left and right, gets the tradingdays starting
         7 days before and 7 days after, then takes the middle one in the list.
         if this is the same as left, takes the next one. -> no weekends/holidays
         Fixed_Bug: when mid falls on a holiday/weekend, it is possible that the last
         one in the list is the same as left, that's why I added the mid+td(7) in the call
         to self.nyse, and the conditional return"""
        mid = left + (right - left) / 2
        mid = NYSE.valid_days(mid- FOURDAYS, mid+ FOURDAYS).tz_localize(None)
        midix = int(len(mid) / 2)
        to_return = mid[midix]
        return to_return if to_return.date() != left.date() else mid[midix + 1]

    def find_first(self, sym, timeframe):

        # first try to get a headtimestamp
        left, right = self.getHead(sym), self.today
        attempt = count(1)
        while "timed out" in left.errors and next(attempt) < 3:
            left = self.getHead(sym)

        # if that doesn't work, set 1990 or return error
        if not left:
            if "No head time stamp" in left.errors:
                left = pd.Timestamp("1990-01-01")
            elif "invalid symbol" in left.errors:
                return "invalid symbol"
            elif "timed out" in left.errors:
                return "timed out getHead"
        else: left = pd.Timestamp(left.data)

        # make the first attempt
        found = self.get(sym, timeframe, left, left)
        if found:  return left

        # track last_test to break out if same date gets tested again, potential infinite loop
        test = self._calc_midpoint(left, right)
        while abs(left - right) >= WEEK:
            found = self.get(sym, timeframe, test, test)

            last_test = test
            if found: right = test
            else: left = test

            test = self._calc_midpoint(left, right)
            # if _calcmidpoint returns the same date, left and right must be very close anyway
            if last_test == test: return test

        return test

    # RECEIVERS
    def headTimestamp(self, id_, stamp):
        response = self[id_].setEnd(stamp)
        self.response(response)

    def historicalData(self, id_, bar): self[id_] + bar

    def historicalDataEnd(self, id_, start, end):
        if self._blacklist(id_): return

        response = self[id_].setEnd(id_, end if end in self.ErrResponses else None)
        self.response(response)

    ## FOR USER
    def NotBlocking(self):
        self.Block = False
        self.directreturn = False

    def Blocking(self, directreturn= True):
        self.Block = True
        self.directreturn = directreturn

    def response(self, response):
        """ overwrite in child class """
        if not self.directreturn:
            print(response.tf, response.sym)
            print(response.df)


    def tf_sym(self, id_):
        try: return self[id_].timeframe, self[id_].orig_sym
        except KeyError: return "Not a used id", "Not a used id"

    def clear(self): self.Reqs.clear()

    def __getitem__(self, id_): return self.Reqs[id_]



class IBRequest:
    """ only used to keep track of speed/errors for each request made to IB"""

    def __init__(self, *req_args):
        self.req, self.id = req_args, req_args[0]
        self.t_requested = self.speed = self.error = None

    def _finalize(self, err):
        self.speed = time() - self.t_requested
        self.error = err

    def __iter__(self):
        self.t_requested = time()
        return iter(self.req)

    def __repr__(self): return str(self.req)


_defcontract = Contract()
class Request:
    """ holds variables and methods needed to set up the requests

    THIS CLASS IS NOT SUPPOSED TO BE USED DIRECTLY, YET.
    Calling HistData.get should result in Response object to be created that should be used
    """

    id = count(1)
    PRICECOLS = ["date", "open", "high", "low", "close", "volume"]
    _datecol = PRICECOLS[0]
    IBDT = "%Y%m%d %H:%M:%S"
    ibtfs = dict(s="sec", m="min", h="hour", D="day", W="W", M="M")
    validibtfs = "1 secs, 5 secs, 10 secs, 15 secs, 30 secs, 1 min, 2 mins, 3 mins, 5 mins, 10 mins, 15 mins, 20 mins," \
                 " 30 mins, 1 hour, 2 hours, 3 hours, 4 hours, 8 hours, 1 day, 1W, 1M".replace(", ", ",").split(",")

    ratios = dict(s=dt.timedelta(seconds=1), m=dt.timedelta(minutes=1), h=dt.timedelta(hours=1),
                  D=dt.timedelta(minutes=60 * 16), W=dt.timedelta(minutes=60 * 16 * 5), M=dt.timedelta(days=60 * 16 * 20))


    _contract_defaults = {k: getattr(_defcontract, k) for k in ['comboLegs', 'comboLegsDescrip', 'conId', 'currency',
                                                                   'deltaNeutralContract', 'exchange', 'includeExpired',
                                                                   'lastTradeDateOrContractMonth', 'localSymbol', 'multiplier',
                                                                   'primaryExchange', 'right', 'secId', 'secIdType', 'secType',
                                                                   'strike', 'symbol', 'tradingClass']}

    _contract_defaults.update({"secType": "STK", "currency": "USD", "exchange": "SMART"})

    @classmethod
    def makeContract(cls, symbol):
        if isinstance(symbol, Contract): return symbol, symbol.symbol

        contract = Contract()

        if isinstance(symbol, dict):
            contract.symbol = symbol["symbol"]
            for att, default in cls._contract_defaults.items():
                setattr(contract, att, symbol.get(att, default))
            return contract, contract.symbol

        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"
        return contract, symbol

    def set_request_dates(self, start, end):
        """
        Sets up start and end dates for the actual requests to IB


        :param start:
        :param end:
        :return:
        """
        if start == end:
            start = nstart = dt.datetime.combine(start.date(), dt.time(0))
            end = nend = dt.datetime.combine(end.date(), dt.time(0)) + dt.timedelta(1)
        else:
            nstart = dt.datetime.combine(start.date(), dt.time(0))
            nend = dt.datetime.combine(end.date(), dt.time(0)) + dt.timedelta(1)
            if end.time() == dt.time(0):
                end = nend

        return start, end, nstart, nend

    def date_duration(self, start, end):
        """
        calculate the duration that I need for the request to IB

        :param start:
        :param end:
        :return:
        """
        diff = max(ceil((end - start).total_seconds()/60/60/24), 1)
        ndays = diff - int(diff//7 *2)
        if not ndays:
            raise ValueError("\n\n --- > no tradingdays in that range")
        if ndays < 365:
            duration = f"{ndays} D"
        else:
            duration = f"{diff // 365 + 1} Y"
        return ndays, duration

    def calc_nreqs(self, tf, ndays):

        tfdelta = self.ratios[tf[-1]] * int(tf[:-1])
        nrows = ceil(ndays * self.ratios["D"] / tfdelta)
        return (nrows // 5000) + 1

    @classmethod
    def _tf(cls, tf):
        x = int(tf[:-1])
        label = cls.ibtfs[tf[-1]]

        if x == 1:
            label = f"{x} {label}"
        else:
            label = f"{x} {label}s"

        if not label in cls.validibtfs:
            raise ValueError(f"only the following tfs are allowed:\n{cls.validibtfs}")
        return label

    @classmethod
    def _ib(cls, dte):
        return dt.datetime.strftime(dte, cls.IBDT)

    def __init__(self, symbol, timeframe, start, end, format_, onlyRTH, type_):
        self.contract, self.symbol = self.makeContract(symbol)
        self.start, self.end, self.nstart, self.nend = self.set_request_dates(start, end)
        ndays = self.date_duration(start, end)[0]  # the duration for IB format
        self.nreqs = self.calc_nreqs(timeframe, ndays)  # necessary number of reqs

        self.timeframe = self._tf(timeframe)
        self.orig_tf = timeframe
        self.data = []

        self._ids = []
        self.ib_requests = {}
        # since the request might need to be split, create each request
        add = (self.nend - self.nstart) / self.nreqs
        for i in range(self.nreqs):
            thisstart = self.nstart + add * i
            thisend = thisstart + add
            duration, end = self.date_duration(thisstart, thisend)[1], self._ib(thisend)

            id_ = next(self.id)
            self._ids.append(id_)
            self.ib_requests[id_] = IBRequest(id_, self.contract, end, duration, self.timeframe,
                                              type_, int(onlyRTH), format_, False, [])

        self.Response = Response(self.symbol, self.orig_tf)
        self.current, self.received = -1, 0
        self.event = Event()

    def __add__(self, bar):
        """ appends the pricedata row as a list to the list of lists in Req.data"""
        self.data.append(
            [bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def setEnd(self, id_, err):
        """ this method finalizes a transmitted request by taking the speed,
        incrementing the received number, and saving potential errors.
        If the last of the required requests has been reached, the df is made
        and the Reponse object finished"""

        self[id_]._finalize(err)
        self.received += 1
        ndata = len(self.data)
        logger.debug("RECEIVED IB-REQUEST --- id: %s nreceived: %s error: %s rows of data: %s",
                     id_, self.received, err, ndata)
        if self.received == self.nreqs:
            logger.info("RECEIVED REQUEST --- rows of data: %s", ndata)
            if ndata: logger.debug("REQUEST DATA --- from %s to %s", self.data[0][0], self.data[-1][0])
            # this makes the dataframe, sorts it, drops duplicates and trims it
            self.data = pd.DataFrame(self.data, columns=self.PRICECOLS)

            d = self._datecol
            self.data[d] = pd.to_datetime(self.data[d], infer_datetime_format=True)
            self.data = self.data.sort_values(d).drop_duplicates(d)

            # if a date (no time) was requested, adjust the end cut off to include the whole day
            if self.end.time() == dt.time(0):
                end = self.end + dt.timedelta(1)
            else:
                end = self.end
            # trim it
            mask = (self.start <= self.data[d]) & (self.data[d] < end)
            self.data = self.data[mask]
            self.data.set_index(d, inplace=True)

            # finish the response object
            self.Response.finalize(self.data, list(self))
            self.event.set()
            return self.Response

        else:
            self.event.set()

    def __getitem__(self, item):
        return self.ib_requests[item]

    def __iter__(self):
        self.__ids = iter(self._ids)
        return self

    def __next__(self):
        return self[next(self.__ids)]


# noinspection PyMissingConstructor
class Stamp(Request):
    def __init__(self, symbol, type_, only_rth, format_):
        self.contract, self.symbol = self.makeContract(symbol)
        id_ = next(self.id)
        self._ids = [id_]
        self.ib_requests = {id_: IBRequest(id_, self.contract, type_, only_rth, format_)}

        self.event = Event()
        self.timeframe = "stamp"
        self.Response = Response(self.symbol, self.timeframe)

    def setEnd(self, stamp):
        if stamp in HistData.ErrResponses:
            err = stamp
        else:
            err = None

        self[self._ids[0]]._finalize(err)
        self.Response.finalize(stamp, list(self))
        self.event.set()
        return self.Response


class Response:
    """ This is the object that will be returned either directly by
    calling the Manager's getHistData method or through the overwritten
    response method"""

    def __init__(self, sym, tf):
        self.sym = sym
        self.tf = tf
        self.data = pd.DataFrame()
        self.nerrors = self.speed = self.nreqs = 0
        self.requests, self.errors, self.success = [], [], False
        self.start = self.end = self.shape = None

    def _updspeed(self, speed, n):
        self.speed = (self.speed * (n - 1) + speed) / n

    def finalize(self, data, reqs):
        """ saves the returned data and sets the success attribute
        if a dataframe was returned, it's considered a success
        if not then its only a success if there are less errors than
        requests"""
        self.data = data
        self.requests = reqs
        self.nreqs = len(reqs)

        self.errors = self.return_errors(drop_duplicates=False)
        self.nerrors = len(self.errors)
        self.speed = self.return_speeds()
        self.full_speed = sum(self.speed)
        self.speed = self.full_speed / len(self.speed)

        if isinstance(data, pd.DataFrame):
            if data.shape[0]:
                self.success = True
                self.shape = data.shape
                if Request._datecol in data.columns:
                    self.start, self.end = data[Request._datecol].iloc[[0, -1]]
                else:
                    self.start, self.end = data.index[[0, -1]]
        else:
            self.success = self.nerrors < self.nreqs

    def return_errors(self, withid=False, drop_duplicates=True):
        if not withid:
            errs = [r.error for r in self.requests if not r.error is None]
            return list(set(errs)) if drop_duplicates else errs
        else:
            return [(r.id, r.error) for r in self.requests]

    def return_speeds(self, withid=False):
        if not withid:
            return [r.speed for r in self.requests]
        else:
            return [(r.id, r.speed) for r in self.requests]

    def __bool__(self):
        return self.success

    def __getitem__(self, ID):
        for req in self.requests:
            if req.id == ID: return req



