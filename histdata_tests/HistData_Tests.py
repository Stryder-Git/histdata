import unittest as ut
from unittest.mock import Mock, patch
from HistData.HistData import HistData
from HistData.Request import Response
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


class With_Cleaning(ut.TestCase):
    """ Here, mainly the use of the CleanResponse method in HistData is tested:
    The manual use, after receiving the uncleaned response when ImmediatelyClean is set to False
    and the automatic use when ImmediatelyClean is set to True """
    def remove_dates_from_test_data(self, name, df):
        changed= False
        if not "Date" in df.columns:
            changed= True
            df.reset_index(inplace= True)

        df = df[~df["Date"].dt.date.isin(self.adjust[name]["dates"])]
        return df.set_index("Date") if changed else df

    @classmethod
    def setUpClass(cls) -> None:
        """
        this sets up a dictionary of dictionaries containing the dates that are removed to test if the cleaner
        fills them correctly.
        The data is also requested here, to avoid having to request it in every test.
        -> it will be kept in cls.responses
        """
        # dates to modify/delete
        cls.adjust = {  "efx": {"start_end": (dt(2010, 3, 10), dt(2010, 3, 29)),
                              "dates": Series([ddt(2010,3,11), ddt(2010,3,17), ddt(2010,3,18), ddt(2010,3,22)])},

                         "acic": {"start_end": (dt(2021, 1, 20), dt(2021, 2, 12)),
                                 "dates": Series([ddt(2021,1,22), ddt(2021,1,27), ddt(2021,1,28), ddt(2021,2,10)])},

                         "qtt": {"start_end": (dt(2018,10,2), dt(2018,12,28)),
                                 "dates": Series([ddt(2018,12,19), ddt(2018,12,20), ddt(2018,12,24), ddt(2018,12,26)])}
        }
        # request the data to be cleaned
        cls.hd = HistData(141654313)
        sleep(3)
        print("\nmaking large requests")
        cls.responses = {sym: cls.hd.get(sym, "1m", *datedct["start_end"]) for sym, datedct in cls.adjust.items()}

    def test_CleanResponse(self):
        """ this will test the CleanResponse as a seperate method"""
        self.hd.Blocking(True)
        self.hd.setImmediatelyCleanTo(False)

        for sym, datedct in self.adjust.items():
            print("doing ", sym)
            dates = datedct["dates"]
            resp = self.responses[sym]
            # get the data and remove the dates
            resp.data = self.remove_dates_from_test_data(sym, resp.data)
            print("got and removed")

            # check if dates are correctly removed
            in_ = dates.isin(resp.data.index.date)
            self.assertFalse(in_.any(), f"{sym}: dates were incorrectly removed {dates[in_]}")

            # run it through the cleaner and check if all dates have been added correctly
            resp = self.hd.CleanResponse(resp)
            in_ = dates.isin(resp.data.index.date)
            self.assertTrue(in_.all(), f"{sym}: dates weren't added: {dates[~in_]}")

            # check if cache of cleaner is empty
            self.assertEqual(len(self.hd.Cleaner.dates_counts), 0, f"{sym}: dates_counts cache wasn't cleared")
            self.assertEqual(len(self.hd.Cleaner.datatoconcat), 0, f"{sym}: datatoconcat cache wasn't cleared")


    def test_Cleaner_methods_as_mocks(self):
        """here the Cleaner module is replaced with a Mock object to verify the automatic
         calling of the methods in the get method"""
        self.hd.Blocking(True)
        self.hd.setImmediatelyCleanTo(True)
        original_makeRequest = self.hd.R.makeRequest
        original_Cleaner = self.hd.Cleaner

        # This will mock the makeRequest method of the Request_Manager, setting the return
        # value to look like the response object
        mock_response = Response("sym", "tf"); mock_response.data = "data"
        self.hd.R.makeRequest = Mock(return_value= mock_response)

        prepare_return = self.hd.Cleaner.Form("sym", "data")
        for sym, datedct in self.adjust.items():
            d = datedct["start_end"][1]
            self.hd.Cleaner = Mock()
            # The Prepare and FillMissingData methods will be mock objects returning the
            # prepare_return object which looks like the namedtuple in the Cleaner
            self.hd.Cleaner.Prepare.return_value = prepare_return
            self.hd.Cleaner.FillMissingData.return_value = prepare_return

            resp = self.hd.get(sym, "1m", d, d)
            self.hd.Cleaner.Prepare.assert_called_once_with(mock_response.sym, mock_response.data)
            # print(self.hd.Cleaner.Prepare.call_args_list)
            self.hd.Cleaner.FillMissingData.assert_called_once_with(prepare_return)
            # print(self.hd.Cleaner.FillMissingData.call_args_list)
            self.hd.Cleaner.clear_cache.assert_called_once_with(prepare_return)
            # print(self.hd.Cleaner.clear_cache.call_args_list)

            self.assertEqual(resp.data, prepare_return.df)

        self.hd.R.makeRequest = original_makeRequest
        self.hd.Cleaner = original_Cleaner


    def test_Cleaner_with_mock_data(self):
        """ This test replaces the MakeRequest response data with the data where some dates are removed to run it
        through the automatically called Cleaner methods"""
        self.hd.Blocking(True)
        self.hd.setImmediatelyCleanTo(True)
        original_makeRequest = self.hd.R.makeRequest

        for sym, datedct in self.adjust.items():
            dates = datedct["dates"]
            self.responses[sym].data = self.remove_dates_from_test_data(sym, self.responses[sym].data)
            self.hd.R.makeRequest = Mock(
                side_effect= Side_Effect({1: self.responses[sym]}, original_makeRequest))

            resp = self.hd.get(sym, "1m", *datedct["start_end"])
            in_ = dates.isin(resp.data.index.date)
            self.assertTrue(in_.all(), f"{sym}: dates weren't added: {dates[~in_]}")

            # check if cache of cleaner is empty
            self.assertEqual(len(self.hd.Cleaner.dates_counts), 0, f"{sym}: dates_counts cache wasn't cleared")
            self.assertEqual(len(self.hd.Cleaner.datatoconcat), 0, f"{sym}: datatoconcat cache wasn't cleared")

        self.hd.R.makeRequest = original_makeRequest


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
        self.assertTrue(all([isinstance(x, float) for x in resp.return_speeds()]),
                        f"{resp.return_speeds()} should all be floats")

        print(resp.return_speeds(), resp.errors)


if __name__ == '__main__':
    ut.main()