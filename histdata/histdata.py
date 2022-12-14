from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract


from threading import Thread, Event
import logging
logger = logging.getLogger(__name__)
import histdata._utils as u

from math import ceil
import datetime as dt
import pandas as pd
import pandas_market_calendars as mcal
from itertools import count
from functools import wraps
from time import time

NYSE = mcal.get_calendar("NYSE")
FOURDAYS = pd.Timedelta("4D")
WEEK = pd.Timedelta("7D")

def _temp_block_skip(meth):
    @wraps(meth)
    def _meth(self, *args, **kwargs):
        prev = self._block
        self.block(True)
        self._skip_response = True
        result = meth(self, *args, **kwargs)
        self._skip_response = False
        self.block(prev)
        return result

    return _meth

def _todt(d):
    return pd.Timestamp(d).to_pydatetime()

def _isError(err):
    return err in HistData.ErrResponses

class HistData(EWrapper, EClient):
    ErrResponses = ["No Data", "invalid symbol", "No head time stamp", "timed out"]
    Reqs = {}
    BLACKLIST = []
    TIMEOUT = 60

    def __init__(self, clientId, host= "127.0.0.1", port= 7497):
        EClient.__init__(self, self)
        self.connect(host, port, clientId)
        Thread(target= self.run, daemon= True).start()
        self._block = True
        self.IBTWSConnected = False
        self._threadwait = True
        self._skip_response = False
        self.today = pd.Timestamp("now").normalize()

    ###########################
    # ibapi receiving methods #
    ###########################
    def nextValidId(self, id_):
        logger.info("connected nextValidId: %s", id_)
        self.IBTWSConnected = True

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
        else:
            self._log_error(logging.DEBUG, id_, code, string, prefix="UNCAUGHT --- ")

    def headTimestamp(self, id_, stamp):
        response = self[id_].setEnd(id_, stamp)
        if self._skip_response: return
        self.response(response)

    def historicalData(self, id_, bar): self[id_] + bar

    def historicalDataEnd(self, id_, start, end):
        logger.debug("HISTORICAL DATA END ------ %s %s %s", id_, start, end)
        if self._blacklist(id_): return

        response = self[id_].setEnd(id_, end if end in self.ErrResponses else None)
        if response is None or self._skip_response: return
        self.response(response)

    @property
    def blocks(self): return self._block

    def _log_error(self, level, id_, code, string, prefix= ""):
        logger.log(level, "%s%s: %s - %s", prefix, id_, code, string)

    @classmethod
    def setTimeOut(cls, seconds): cls.TIMEOUT = seconds

    @staticmethod
    def isResponse(obj): return isinstance(obj, Response)

    def isError(self, err_msg): return _isError(err_msg)

    def _transmit_request(self, request):
        isStamp = isinstance(request, Stamp)
        func = self.reqHeadTimeStamp if isStamp else self.reqHistoricalData

        for req in request:
            self.Reqs[req.id] = request
            if self._threadwait: request.event.clear()
            logger.debug("SENDING REQUEST --- %s", req)
            func(*req)
            if self._threadwait and not request.event.wait(self.TIMEOUT):
                logger.info("EVENT TIMEOUT --- request id: %s", req.id)
                self.BLACKLIST.append(req.id)
                request.setEnd(req.id, "timed out")

    def transmit_request(self, request):
        if self._block:
            self._transmit_request(request)
        else:
            Thread(target=self._transmit_request, args=(request,)).start()

        return request.response

    def getHead(self, symbol, type_= "TRADES", onlyRTH= False, format_= 1):
        # set the Stamp with: request args, symbol, and Event to be waited for
        request = Stamp(symbol, type_, onlyRTH, format_)
        return self.transmit_request(request)

    def get(self, symbol, timeframe, start, end, format_=1, onlyRTH=False, type_="TRADES"):
        start, end = _todt(start), _todt(end)
        request = Request(symbol, timeframe, start, end, format_, onlyRTH, type_)
        return self.transmit_request(request)

    def ishistdatareq(self, id_): return not isinstance(self.Reqs[id_], Stamp)

    def _blacklist(self, id_):
        if id_ in self.BLACKLIST:
            logger.info(f"{self[id_].symbol}: {self[id_].orig_tf} @{self[id_][id_].t_requested}\n"
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

    @_temp_block_skip
    def find_first(self, sym, timeframe):
        resp = Response(u.make_contract(sym), timeframe)

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
                return resp.finalize("invalid symbol")
            elif "timed out" in left.errors:
                return resp.finalize("timed out")
        else: left = pd.Timestamp(left.data)

        # make the first attempt
        found = self.get(sym, timeframe, left, left)
        if found: return resp.finalize(left)

        # track last_test to break out if same date gets tested again, potential infinite loop
        test = self._calc_midpoint(left, right)
        while abs(left - right) >= WEEK:
            found = self.get(sym, timeframe, test, test)

            last_test = test
            if found: right = test
            else: left = test

            test = self._calc_midpoint(left, right)
            # if _calcmidpoint returns the same date, left and right must be very close anyway
            if last_test == test: break

        return resp.finalize(test)

    def block(self, bool_= True):
        self._block = bool_

    def response(self, response):
        """ overwrite in child class """
        return response

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



class Request:
    """ holds variables and methods needed to set up the requests

    THIS CLASS IS NOT SUPPOSED TO BE USED DIRECTLY, YET.
    Calling histdata.get should result in Response object to be created that should be used
    """

    id = count(1)
    PRICECOLS = ["date", "open", "high", "low", "close", "volume"]
    _datecol = PRICECOLS[0]
    IBDT = "%Y%m%d %H:%M:%S"
    ratios = dict(s=dt.timedelta(seconds=1), m=dt.timedelta(minutes=1), h=dt.timedelta(hours=1),
                  D=dt.timedelta(minutes=60 * 16), W=dt.timedelta(minutes=60 * 16 * 5), M=dt.timedelta(days=60 * 16 * 20))

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
    def _ib(cls, dte):
        return dt.datetime.strftime(dte, cls.IBDT)

    def __init__(self, symbol, timeframe, start, end, format_, onlyRTH, type_):
        self.contract = u.make_contract(symbol)
        self.response = Response(self.contract, timeframe)

        self.start, self.end, self.nstart, self.nend = self.set_request_dates(start, end)
        ndays = self.date_duration(start, end)[0]  # the duration for IB format
        self.nreqs = self.calc_nreqs(timeframe, ndays)  # necessary number of reqs

        self.data = []
        self.ib_requests = {}
        # since the request might need to be split, create each request
        add = (self.nend - self.nstart) / self.nreqs
        for i in range(self.nreqs):
            thisstart = self.nstart + add * i
            thisend = thisstart + add
            duration, end = self.date_duration(thisstart, thisend)[1], self._ib(thisend)

            id_ = next(self.id)
            self.ib_requests[id_] = IBRequest(id_, self.contract, end, duration,
                                              u.ibtfs[pd.Timedelta(timeframe)],
                                              type_, int(onlyRTH), format_, False, [])

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
        logger.debug("RECEIVED IB-REQUEST --- id: %s nreceived: %s/%s error: %s rows of data: %s",
                     id_, self.received, self.nreqs, err, ndata)
        if self.received == self.nreqs:
            logger.info("RECEIVED REQUEST --- rows of data: %s", ndata)
            if ndata: logger.debug("REQUEST DATA --- from %s to %s", self.data[0][0], self.data[-1][0])
            # this makes the dataframe, sorts it, drops duplicates and trims it
            data = pd.DataFrame(self.data, columns=self.PRICECOLS)

            d = self._datecol
            data[d] = pd.to_datetime(data[d], infer_datetime_format=True)
            data = data.sort_values(d).drop_duplicates(d)

            # if a date (no time) was requested, adjust the end cut off to include the whole day
            if self.end.time() == dt.time(0):
                end = self.end + dt.timedelta(1)
            else:
                end = self.end
            # trim it
            mask = (self.start <= data[d]) & (data[d] < end)
            data = data[mask]
            data.set_index(d, inplace=True)

            # finish the response object
            self.response.finalize(data, list(self))
            self.event.set()
            return self.response

        else:
            self.event.set()

    def __getitem__(self, item):
        return self.ib_requests[item]

    def __iter__(self):
        return iter(self.ib_requests.values())


# noinspection PyMissingConstructor
class Stamp(Request):
    def __init__(self, symbol, type_, only_rth, format_):
        self.contract = u.make_contract(symbol)
        id_ = next(self.id)
        self.ib_requests = {id_: IBRequest(id_, self.contract, type_, only_rth, format_)}

        self.event = Event()
        self.timeframe = "stamp"
        self.response = Response(self.contract, self.timeframe)

    def setEnd(self, id_, stamp):
        if _isError(stamp): err = stamp
        else: err = None

        self[id_]._finalize(err)
        self.response.finalize(stamp, list(self))
        self.event.set()
        return self.response


class Response:
    """ This is the object that will be returned either directly by
    calling the Manager's getHistData method or through the overwritten
    response method"""

    def __init__(self, contract, tf):
        self.contract = contract
        self.sym = contract.symbol
        self.tf = tf
        self.data = self.start = self.end = self.shape = None
        self.nerrors = self.speed = self.full_speed = self.nreqs = 0
        self.requests, self.errors, self.success = [], [], False
        self.ready = False

    def _updspeed(self, speed, n):
        self.speed = (self.speed * (n - 1) + speed) / n

    def finalize(self, data, reqs= None):
        """ saves the returned data and sets the success attribute
        if a dataframe was returned, it's considered a success
        if not then its only a success if there are less errors than
        requests"""
        logger.info("finalizing response with: %s", data)
        # find_first head response
        if reqs is None:
            if _isError(data):
                self.errors = [data]
                self.nerrors = 1
            else:
                self.data = _todt(data)
                self.success = True

            self.ready = True
            return self

        self.requests = reqs
        self.nreqs = len(reqs)

        self.errors = self.get_errors(drop_duplicates=False)
        self.nerrors = len(self.errors)
        self.speed = self.get_speeds()
        self.full_speed = sum(self.speed)
        self.speed = self.full_speed / len(self.speed)

        # historical data request always returns dataframe
        if isinstance(data, pd.DataFrame):
            self.data = data
            if data.shape[0]:
                self.shape = data.shape
                self.start, self.end = data.index[[0, -1]]
                self.success = True

        # getHead might return an error message instead of a date
        elif isinstance(data, str) and not _isError(data):
            self.data = _todt(data)
            self.success = True

        self.ready = True
        return self

    def get_errors(self, withid=False, drop_duplicates=True):
        if not withid:
            errs = [r.error for r in self.requests if not r.error is None]
            return list(set(errs)) if drop_duplicates else errs
        else:
            return [(r.id, r.error) for r in self.requests]

    def get_speeds(self, withid=False):
        if not withid:
            return [r.speed for r in self.requests]
        else:
            return [(r.id, r.speed) for r in self.requests]

    def __bool__(self):
        return self.success

    def __getitem__(self, ID):
        for req in self.requests:
            if req.id == ID: return req



