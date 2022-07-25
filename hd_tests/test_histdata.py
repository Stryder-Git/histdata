import pandas as pd
import pytest
from HistData.HistData import HistData, Response

from datetime import datetime as dt

@pytest.fixture(scope= "module")
def histdata():
    HistData.DEF_CLIENTID = 8888
    HistData.setTimeOut(30)
    hd = HistData()
    print("\nconnected: ", hd.isConnected(), "\n")
    yield hd
    hd.disconnect()
    print("\nconnected: ", hd.isConnected(), "\n")

@pytest.fixture
def hd_block_direct(histdata):
    histdata.Blocking(True)
    return histdata

@pytest.fixture
def hd_block_notdirect(histdata):
    histdata.Blocking(False)
    return histdata

@pytest.fixture
def hd_notblock(histdata):
    histdata.NotBlocking()
    return histdata

def test_blocking_direct(hd_block_direct):
    assert hd_block_direct.Block and hd_block_direct.directreturn

def test_blocking_notdirect(hd_block_notdirect):
    assert hd_block_notdirect.Block and not hd_block_notdirect.directreturn

def test_notblocking(hd_notblock):
    assert not hd_notblock.Block and not hd_notblock.directreturn

@pytest.mark.parametrize("req, result", [
    (("aapl", "1h", dt(2010,1,1), dt(2010,3,5)),
     ((668,5), dt(2010,1,4,4), dt(2010,3,5,19))),
    (("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15)),
     ((100,5), dt(2006,10,11,13), dt(2006,10,17,14)))
])

def test_get_blocking_direct_success(req, result, hd_block_direct):
    resp = hd_block_direct.get(*req)

    assert isinstance(resp, Response)
    assert isinstance(resp.data, pd.DataFrame)

    assert resp.shape == result[0]
    assert resp.start == pd.Timestamp(result[1])
    assert resp.end == pd.Timestamp(result[2])




    #
    # aapl = hd.get("AAPL", "1D", dt.datetime(2000, 1, 1), dt.datetime(2000, 1, 5))
    # fb = hd.get("FB", "30m", "2020-01-01", "2020-01-05")
    # assert isinstance(fb, Response)
    # assert isinstance(fb.data, pd.DataFrame)



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

