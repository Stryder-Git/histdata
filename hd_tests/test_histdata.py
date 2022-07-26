import pandas as pd
import pytest
from datetime import datetime as dt
from collections import namedtuple
from HistData.HistData import HistData, Response

# import logging
# import sys
#
# logger = logging.getLogger("HistData.HistData")
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(1)
# logger.addHandler(handler)
# logger.setLevel(1)



@pytest.fixture(scope= "module")
def histdata():
    HistData.DEF_CLIENTID = 8887
    HistData.setTimeOut(30)
    hd = HistData()
    yield hd
    hd.disconnect()

@pytest.fixture
def check_connect(histdata):
    if not histdata.isConnected():
        pytest.skip("Could not connect to TWS\n"
                    "Either TWS is not running or you are running the tests too often\n"
                    "since IB throttles requests.", allow_module_level= True)
    return histdata

@pytest.fixture
def hd_block_direct(check_connect):
    check_connect.Blocking(True)
    return check_connect

@pytest.fixture
def hd_block_notdirect(check_connect):
    check_connect.Blocking(False)
    return check_connect

@pytest.fixture
def hd_notblock(check_connect):
    check_connect.NotBlocking()
    return check_connect



def test_blocking_direct(hd_block_direct):
    assert hd_block_direct.Block and hd_block_direct.directreturn

def test_blocking_notdirect(hd_block_notdirect):
    assert hd_block_notdirect.Block and not hd_block_notdirect.directreturn

def test_notblocking(hd_notblock):
    assert not hd_notblock.Block and not hd_notblock.directreturn


R = namedtuple("R", ["shape", "start", "end", "errors"])

@pytest.mark.parametrize("req, result", [
    (("aapl", "1h", dt(2010,1,1), dt(2010,3,5)),
     R((668,5), dt(2010,1,4,4), dt(2010,3,5,19), [])),
    (("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15)),
     R((100,5), dt(2006,10,11,13), dt(2006,10,17,14), [])),
    (("fb", "1m", dt(2005,4,1,15,23), dt(2005,4,12,11,15)),
     R(None, None, None, ["No Data", "No Data"])),
])

def test_get_blocking_direct_success(req, result, hd_block_direct):
    resp = hd_block_direct.get(*req)

    assert isinstance(resp, Response)
    assert isinstance(resp.data, pd.DataFrame)

    assert resp.shape == result.shape
    assert resp.start == pd.Timestamp(result.start)
    assert resp.end == pd.Timestamp(result.end)
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

