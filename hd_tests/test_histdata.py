import pandas as pd

from HistData.HistData import HistData, Response

import datetime as dt

HistData.DEF_CLIENTID = 8888
HistData.setTimeOut(30)
def test_get():
    hd = HistData()

    aapl = hd.get("AAPL", "1D", dt.datetime(2000, 1, 1), dt.datetime(2000, 1, 5))
    assert isinstance(aapl, Response)
    assert isinstance(aapl.data, pd.DataFrame)

    fb = hd.get("FB", "30m", "2020-01-01", "2020-01-05")
    assert isinstance(fb, Response)
    assert isinstance(fb.data, pd.DataFrame)

    hd.disconnect()


def test_getHead():
    hd = HistData()
    aapl_stamp = hd.getHead("AAPL")
    assert isinstance(aapl_stamp, Response)
    assert isinstance(aapl_stamp.data, str)
    hd.disconnect()


def test_find_first():
    return

if __name__ == '__main__':

    for ref, obj, in locals().copy().items():
        if ref.startswith("test_"):
            print("running: ", ref)
            obj()

