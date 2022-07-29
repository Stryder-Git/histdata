import pandas as pd
import pytest
from datetime import datetime as dt
from collections import namedtuple
from histdata.histdata import HistData, Response

# import logging
# import sys
#
# logger = logging.getLogger("histdata.histdata")
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(1)
# logger.addHandler(handler)
# logger.setLevel(1)



@pytest.fixture(scope= "module")
def histdata():
    HistData.setTimeOut(10)
    hd = HistData(7777)
    if not hd.isConnected():
        pytest.skip("Not connected to TWS\n", allow_module_level= True)
    yield hd
    hd.disconnect()

@pytest.fixture
def hd_block(histdata):
    histdata.block()
    return histdata

@pytest.fixture
def hd_notblock(histdata):
    histdata.block(False)
    return histdata

def test_blocking(hd_block):
    assert hd_block.blocks

def test_notblocking(hd_notblock):
    assert not hd_notblock.blocks


def _get_check(func, *args, **kwargs):
    res = func(*args, **kwargs)
    if not func.__self__.isConnected():
        pytest.xfail("Lost connection to TWS\n")
    return res


R = namedtuple("R", ["shape", "start", "end", "errors"])

@pytest.mark.parametrize("req, result", [
    (("aapl", "1h", dt(2010,1,1), dt(2010,3,5)),
     R((668,5), dt(2010,1,4,4), dt(2010,3,5,19), [])),
    (("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15)),
     R((100,5), dt(2006,10,11,13), dt(2006,10,17,14), [])),
    (("fb", "1m", dt(2005,4,1,15,23), dt(2005,4,12,11,15)),
     R(None, None, None, ["invalid symbol", "invalid symbol"])),
])
def test_get_blocking(req, result, hd_block):
    resp = _get_check(hd_block.get, *req)

    assert isinstance(resp, Response)
    assert isinstance(resp.data, pd.DataFrame)

    assert resp.shape == result.shape
    assert resp.start == (None if result.start is None else pd.Timestamp(result.start))
    assert resp.end == (None if result.end is None else pd.Timestamp(result.end))
    assert resp.errors == result.errors


# def test_getHead(hd):
#     aapl_stamp = hd.getHead("AAPL")
#     assert isinstance(aapl_stamp, Response)
#     assert isinstance(aapl_stamp.data, str)
#

def test_find_first():
    return

if __name__ == '__main__':

    for ref, obj, in locals().copy().items():
        if ref.startswith("test_"):
            print("running: ", ref)
            obj()

