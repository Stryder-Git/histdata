from HistData import HistData

import datetime as dt



def test_stock_price_data():
    hd = HistData()

    aapl = hd.get("AAPL", "1D", dt.datetime(2000, 1, 1), dt.datetime(2000, 1, 5))
    print(aapl.data)
    print(aapl.speed)
    hd.disconnect()


def test_headtimestamp():
    hd = HistData()
    aapl_stamp = hd.getHead("AAPL")
    print(aapl_stamp)
    hd.disconnect()

if __name__ == '__main__':

    for ref, obj, in locals().copy().items():
        if ref.startswith("test_"):
            print("running: ", ref)
            obj()

