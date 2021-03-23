#
# from HistData import HistData
# from datetime import datetime as dt
#
# hd = HistData(15615)
#
# print(hd.get("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15)))
# print(hd.get("aapl", "1h", dt(2010,1,1), dt(2010,3,5)))

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from pandas import DataFrame, to_datetime
from threading import Thread
from Request import Request_Maker
from time import sleep


class Tester(EWrapper, EClient):
    cols = "Date Open High Low Close Volume".split()

    def __init__(self, clientid):
        EClient.__init__(self, self)
        self.connect('127.0.0.1', 7497, clientid)
        Thread(target= self.run, daemon= True).start()
        self.req = []

    def makeContract(self, sym):
        return Request_Maker.makeContract(sym)[0]

    def historicalData(self, reqId, bar):
        self.req.append([bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume])

    def historicalDataEnd(self, reqId:int, start:str, end:str):
        df = DataFrame(self.req, columns= self.cols)
        df["Date"] = to_datetime(df["Date"], infer_datetime_format= True)
        print("first two rows: \n", df.head(2))
        print("\nlast two rows: \n", df.tail(2))
        self.req.clear()

    def disconnect(self):
        super().disconnect()
        exit()

tester = Tester(18974348)
sleep(2)

c = tester.makeContract("aapl")
def req(duration, end):
    print(f"request of duration {duration} and end at {end}")
    tester.reqHistoricalData(1, c, end, duration, "30 mins", "TRADES", 0, 1, False, [])



req("2 D", "20210319 12:35")
























