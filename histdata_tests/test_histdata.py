import pandas as pd

from HistData.HistData import HistData, Response

import datetime as dt

HistData.DEF_CLIENTID = 8888

def test_stock_price_data():
    hd = HistData()

    aapl = hd.get("AAPL", "1D", dt.datetime(2000, 1, 1), dt.datetime(2000, 1, 5))
    assert isinstance(aapl, Response)
    assert isinstance(aapl.data, pd.DataFrame)

    hd.disconnect()


def test_headtimestamp():
    hd = HistData()
    aapl_stamp = hd.getHead("AAPL")
    assert isinstance(aapl_stamp, Response)
    assert isinstance(aapl_stamp.data, str)
    hd.disconnect()

if __name__ == '__main__':

    for ref, obj, in locals().copy().items():
        if ref.startswith("test_"):
            print("running: ", ref)
            obj()

