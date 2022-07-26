import unittest as ut
from unittest.mock import Mock, patch
from HistData.HistData import HistData
from HistData.HistData import Response
from threading import Event
from datetime import datetime as dt, date as ddt, timedelta as td
from time import sleep
from pandas import Series


class Side_Effect:
    def __init__(self, mock_when_what, original_to_call):
        self.when_to_mock = mock_when_what.keys()
        self.mock_return = mock_when_what
        self.counter = 0
        self.original_to_call = original_to_call

    def __call__(self, *args, **kwargs):
        self.counter += 1
        if self.counter in self.when_to_mock:
            return self.mock_return[self.counter]
        else: return self.original_to_call(*args, **kwargs)



class Without_Cleaning(ut.TestCase, HistData):
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
            def __init__(self):
                super().__init__(self, clientid= 5326)
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


class Break_HistData(ut.TestCase):
    """When threadingEvent times out, the received counter increments.
    This causes a premature finalization and return of the response object if
    the request (that took too long) still arrives. (it would increment twice)

    This is a test for the solution, which is the blacklisting of the id of the request
    that times out, and not calling the add/end/receivedtimestamp methods if a response
    is eventually received.
    """
    @classmethod
    def setUpClass(cls) -> None:
        cls.today = dt.now()
        cls.twoweeksago = cls.today - td(14)

    def setUp(self) -> None:
        self.hd = HistData(34814543)
        sleep(3); print("starting test")
    def tearDown(self) -> None: self.hd.disconnect()

    def delaydecorator(self, f, n):
        """ this delaus the call to f by 5 seconds if the first argument to newf is equal to n"""
        def newf(*args):
            if args[0] == n: sleep(5)
            return f(*args)
        return newf

    def test_price_blocking_directreturn(self):
        """ (without blacklisting:) when request 1 times out, and its response is still received before the
        second request's response, it will trigger the finalization of the Response obj too soon.

        >   >    Test Setup:
        The event in Request.Request is patched and set to return False at the first call to wait (simulating timeout),
        then the second request is delayed (using self.delaydecorator) to ensure that the first response
        still arrives before it. This recreates  the double increment effect, causing
        'TypeError: unsupported operand type' in the finalizeation of the Request.Response object.

        >> To recreate the error it should be sufficient to comment out the Request_Manager.BLACKLIST.append(id_)
        line in the transmit method in Request.Request, after the call to self.EndEvent.wait"""

        e = Event()
        self.hd.reqHistoricalData = self.delaydecorator(self.hd.reqHistoricalData, 2)
        with patch("Request.Event", new= Mock(return_value= e)): # replace inaccessible event with e
            e.wait = Mock(side_effect= Side_Effect({1: False}, e.wait)) # set e.wait to custom side_effect
            resp = self.hd.get("aapl", "1m", self.twoweeksago, self.today)

        self.assertListEqual([1], self.hd.R.BLACKLIST, f"{self.hd.R.BLACKLIST} should be [1]")
        self.assertListEqual(["timed out"], resp.errors, f"{resp.errors} should be ['timed out']")
        self.assertTrue(all([isinstance(x, float) for x in resp.get_speeds()]),
                        f"{resp.get_speeds()} should all be floats")

        print(resp.get_speeds(), resp.errors)


if __name__ == '__main__':
    ut.main()