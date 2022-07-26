from collections import namedtuple
from datetime import datetime as dt
import pandas as pd
import pytest

from HistData.HistData import HistData, Response
"""
how to mock

* blocking



I need to mock methods returning data

    * headTimestamp
    -> reqHeadTimeStamp

    * historicalData
    -> reqHistoricalData
    * historicalDataEnd
        -> at end of historicalData

    * error
        -> any interaction




"""
Bar = namedtuple("Bar", ["date", "open", "high", "low", "close", "volume"])

class HistDataMock(HistData):
    _test_data = {
        ("aapl", "1 hour"): [
            ["2010-01-04 04:00:00", 1, 2, 3, 4, 5],
            ["2010-01-06 09:30:00", 1, 2, 3, 4, 5],
            ["2010-03-05 19:00:00", 1, 2, 3, 4, 5],
        ],
        ("amzn", "30 mins"): [
            ["2006-10-11 13:00:00", 1, 2, 3, 4, 5],
            ["2006-10-15 12:00:00", 1, 2, 3, 4, 5],
            ["2006-10-17 14:00:00", 1, 2, 3, 4, 5],
        ],
        ("fb", "1 min"): ["No security definition"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.IBTWSConnected = True
    def connect(self, *args, **kwargs): return
    run = connect

    def reqHistoricalData(self, reqId, contract, end, dur, tf, *args):
        data = self._test_data[(contract.symbol, tf)]
        if not isinstance(data[0], list):
            self.error(reqId, 0, data[0])
            return

        for d in data:
            d = Bar(*d)
            self.historicalData(reqId, d)
        self.historicalDataEnd(reqId, "start", "end")


hdm = HistDataMock()
R = namedtuple("R", ["shape", "start", "end", "errors"])

@pytest.mark.parametrize("req, result", [
    (("aapl", "1h", dt(2010,1,1), dt(2010,3,5)),
     R((3, 5), dt(2010,1,4,4), dt(2010,3,5,19), [])),
    (("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15)),
     R((3, 5), dt(2006,10,11,13), dt(2006,10,17,14), [])),
    (("fb", "1m", dt(2005,4,1,15,23), dt(2005,4,12,11,15)),
     R(None, None, None, ["invalid symbol", "invalid symbol"])),
])

def test_get(req, result):

    resp = hdm.get(*req)
    assert isinstance(resp, Response)
    assert isinstance(resp.data, pd.DataFrame)

    assert resp.shape == result.shape
    assert resp.start == (None if result.start is None else pd.Timestamp(result.start))
    assert resp.end == (None if result.end is None else pd.Timestamp(result.end))
    assert resp.errors == result.errors










