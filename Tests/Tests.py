import unittest as ut
from HistData import HistData
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
        cls.failresults = [
            ["No Data", "No Data"],
        ]

        # cls.headrequests = ["aer", "cs", "fcx",
        #                     "wkhs", "pza", ]
        # cls.headresults = ["20061121  14:30:00", "20010925  13:30:00", "19950710  13:30:00",
        #                    "No head time stamp", "No head time stamp"]



        cls.responseEvent = Event()
        cls.received = {}
        class InnerTest(HistData):
            def __init__(self):
                HistData.__init__(self, 5326)
            def response(self, res):
                if res:
                    cls.received[res.sym] = (res.data.shape, res.data.index[0], res.data.index[-1])
                else:
                    cls.received[res.sym] = res.errors
                cls.responseEvent.set()

        cls.inner = InnerTest()
        sleep(3)

    def test_NotBlocking(self) -> None:
        self.inner.NotBlocking()
        for i, test in enumerate(self.successruns):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()
            self.assertIsNone(direct, "the directreturn should be None but isn't")
            self.assertTupleEqual(self.received[test[0]], self.successresults[i])

        for i, test in enumerate(self.failruns):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()

            self.assertIsNone(direct, "the directreturn should be None but isn't")
            self.assertEqual(self.received[test[0]], self.failresults[i])

    def test_Blocking(self):
        self.received.clear()
        self.inner.Blocking(True)

        for i, test in enumerate(self.successruns):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct,"the directreturn is None but shouldnt be")
            self.assertTupleEqual((direct.data.shape, direct.data.index[0], direct.data.index[-1]),
                                  self.successresults[i])

        for i, test in enumerate(self.failruns):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct, "the directreturn is None but shouldnt be")
            self.assertEqual(direct.errors, self.failresults[i])

    #
    # def test_HeadStamp(self):
    #




if __name__ == '__main__':
    ut.main(verbosity= 2)

