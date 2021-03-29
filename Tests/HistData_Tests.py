import unittest as ut
from HistData import HistData
from threading import Event
from datetime import datetime as dt
from pandas import DataFrame
from time import sleep

class HistDataTests_WithoutCleaning(ut.TestCase, HistData):
    """ These tests check if the response object, and the (not)blocking/directreturn
    combinations work as they should in their most common usage. The response object is
    checked in the different blocking/return combinations, partially implicitly"""
    @classmethod
    def setUpClass(cls) -> None:
        # Requests and results for pricedata requests
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
        # Requests and results for headtimestamp requests
        cls.headrequests = ["aer", "cs", "fcx",
                            "wkhs", "pza"]
        cls.headresults = ["20061121  14:30:00", "20010925  13:30:00", "19950710  13:30:00",
                           ["No head time stamp"], ["No head time stamp"]]

        # The objects required for the actual requests
        cls.responseEvent = Event()
        cls.received = {}
        class InnerTest(HistData):
            def __init__(self): HistData.__init__(self, 5326)
            def response(self, res):
                cls.received[res.sym] = res
                cls.responseEvent.set()

        cls.inner = InnerTest()
        sleep(3)

    def setUp(self) -> None: self.received.clear()  # clear the dict of responses

    def test_Pricedata_NotBlocking(self) -> None:           ## PRICEDATA
        """Making Requests where the call to HistData doesn't block
        and the response will be handled by the seperate response method"""
        self.inner.NotBlocking()

        # Pricedata reqs that should return valid requests
        for test, result in zip(self.successruns, self.successresults):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()
            self.assertIsNone(direct, f"the directreturn should be None but isn't {test[0]}")

            direct = self.received[test[0]]
            self.assertTupleEqual((direct.shape, direct.start, direct.end), result,
                                  f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")

        # PriceData Requests that are supposed to fail
        for test, result in zip(self.failruns, self.failresults):
            self.responseEvent.clear()
            direct = self.inner.get(*test)
            self.responseEvent.wait()
            self.assertIsNone(direct, f"the directreturn should be None but isn't {test[0]}")

            direct = self.received[test[0]]
            self.assertEqual(direct.errors, result,
                             f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")


    def test_Pricedata_BlockingDirect(self):            ## PRICEDATA
        """Making Requests where the call to HistData does block AND Return the response """

        self.inner.Blocking(True)
        # Successful requests
        for test, result in zip(self.successruns, self.successresults):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct, f"the directreturn is None but shouldnt be {test[0]}")
            self.assertTupleEqual((direct.shape, direct.start, direct.end), result,
                                  f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")

        # Failed requests
        for test, result in zip(self.failruns, self.failresults):
            direct = self.inner.get(*test)
            self.assertIsNotNone(direct, f"the directreturn is None but shouldnt be {test[0]}")
            self.assertEqual(direct.errors, result,
                             f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")


    def test_Pricedata_BlockingNotDirect(self):         ## PRICEDATA
        """Making Requests where the call to HistData does block BUT
        the response will be handled by the seperate response method"""
        self.inner.Blocking(False)

        # Successfull requests
        for test, result in zip(self.successruns, self.successresults):
            direct = self.inner.get(*test)
            self.assertIsNone(direct, f"the directreturn should be None but isn't {test[0]}")

            direct =self.received[test[0]]
            self.assertTupleEqual((direct.shape, direct.start, direct.end), result,
                                  f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")

        # Failed requests
        for test, result in zip(self.failruns, self.failresults):
            direct = self.inner.get(*test)
            self.assertIsNone(direct, f"the directreturn should be None but isn't {test[0]}")

            direct = self.received[test[0]]
            self.assertEqual(direct.errors, result,
                             f"result is not what it's supposed to be in {test[0]}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test[0]}")


    def test_headStamp_NotBlocking(self):           ## HEADSTAMP
        """Making Requests where the call to HistData doesn't block
        and the response will be handled by the seperate response method"""

        self.inner.NotBlocking()
        # All Head Stamp Requests
        for test, result in zip(self.headrequests, self.headresults):
            self.responseEvent.clear()
            direct = self.inner.getHead(test)
            self.responseEvent.wait()
            self.assertIsNone(direct, f"the directreturn should be None but isn't {test}")

            direct = self.received[test]
            check = direct.data if direct else direct.errors
            self.assertIn(check, [["timed out"], result],
                        f"result is not what it's supposed to be in {test}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test}")


    def test_headStamp_BlockingDirect(self):            ## HEADSTAMP
        """Making Requests where the call to HistData does block AND return the Response """
        self.inner.Blocking(True)

        # All Head Stamp Requests
        for test, result in zip(self.headrequests, self.headresults):
            direct = self.inner.getHead(test)
            self.assertIsNotNone(direct, f"the directreturn is None but shouldnt be: {test}")

            check = direct.data if direct else direct.errors
            self.assertIn(check, [["timed out"], result],
                        f"result is not what it's supposed to be in {test}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test}")


    def test_headStamp_BlockingNotDirect(self):         ## HEADSTAMP
        """Making Requests where the call to HistData does block BUT
        the response will be handled by the seperate response method"""

        self.inner.Blocking(False)
        # All Head Stamp Requests
        for test, result in zip(self.headrequests, self.headresults):
            direct = self.inner.getHead(test)
            self.assertIsNone(direct, f"the directreturn should be None but isn't: {test}")

            direct = self.received[test]
            check = direct.data if direct else direct.errors
            self.assertIn(check, [["timed out"], result],
                        f"result is not what it's supposed to be in {test}")
            self.assertIsInstance(direct.speed, float, f"speed is not a float in {test}")



class HistDataTests_WithCleaning(ut.TestCase, HistData):
    """ Here, mainly the use of the CleanResponse method in HistData is tested:
    This will be the manual use, after receiving the uncleaned response when ImmediatelyClean
    is set to False and the automatic use when ImmediatelyClean is set to True """
    @classmethod
    def setUpClass(cls) -> None:
        pass


if __name__ == '__main__':
    ut.main()

