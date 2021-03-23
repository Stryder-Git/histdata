import unittest as ut
from HistData.HistData import HistData
from threading import Event
from datetime import datetime as dt
from pandas import DataFrame
from time import sleep

class HistDataTests(ut.TestCase, HistData):
    @classmethod
    def setUpClass(cls) -> None:
        cls.successruns = [
            ("aapl", "1h", dt(2010,1,1), dt(2010,3,5)),
            ("amzn", "30m", dt(2006, 10, 11, 12, 40), dt(2006, 10, 17, 14, 15))
        ]
        cls.successresults = [
            ((668,5), dt(2010,1,4,4), dt(2010,3,5,19)),
            ((100,5), dt(2006,10,11,13), dt(2006,10,17,14))
        ]
        cls.failruns = [
            ("fb", "1m", dt(2005,4,1,15,23), dt(2005,4,12,11,15)),
        ]
        cls.failresults = ["No Data"]

        cls.responseEvent = Event()
        cls.received = {}

        class InnerTest(HistData):
            def __init__(self):
                HistData.__init__(self, 5326)
            def response(self, tf, sym, df):
                if not isinstance(df, str):
                    cls.received[sym] = (df.shape, df.index[0], df.index[-1])
                else:
                    cls.received[sym] = df
                cls.responseEvent.set()

        cls.inner = InnerTest()
        sleep(3)

    def test_NotBlocking(self) -> None:
        self.inner.NotBlocking()
        for i, test in enumerate(self.successruns):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()
            self.assertIs(direct, None, "the directreturn should be None but isn't")
            self.assertTupleEqual(self.received[test[0]], self.successresults[i])

        for i, test in enumerate(self.failruns):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()

            self.assertIs(direct, None, "the directreturn should be None but isn't")
            self.assertEqual(self.received[test[0]], self.failresults[i])

    def test_Blocking(self):
        self.received.clear()
        self.inner.Blocking(True)

        for i, test in enumerate(self.successruns):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct,"the directreturn is None but shouldnt be")
            self.assertTupleEqual((direct.shape, direct.index[0], direct.index[-1]),
                                  self.successresults[i])

        for i, test in enumerate(self.failruns):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct, "the directreturn is None but shouldnt be")
            self.assertEqual(direct, self.failresults[i])





if __name__ == '__main__':
    ut.main()

