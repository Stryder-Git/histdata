import unittest as ut
from datetime import datetime as dt, date as ddt
from pandas import Series

from HistData import Cleaner
from Fetcher import Fetcher

testpd = Fetcher("cleaner_test")
class Cleaner_GeneralTest(ut.TestCase):
    """ This test is appropriate for testing the cleaner as a standalone module, which will then
    automatically instantiate and use a new instance of the HistData class for it's data requests"""

    @classmethod
    def setUpClass(cls) -> None:
        """ This sets up the data to be cleaned in the testruns. They are stored in the 'cleaner_test'
        database and will have 4 dates removed. EFX will also have a few hours cut out of a day to check
        the filling of incomplete days"""
        cls.cleaner = Cleaner(clientid = 123465789)

        cls.efx = testpd.fetch("efx")
        cls.efxdates = Series([ddt(2010,1,15), ddt(2010,2,10), ddt(2010,2,11), ddt(2010,3,22)])
        cls.efxinc = dt(2010,2,2, 11,45), dt(2010,2,2, 15,30)
        cls.efx = cls.efx[~cls.efx["Date"].dt.date.isin(cls.efxdates)]
        cls.efx = cls.efx.loc[~((cls.efxinc[0]< cls.efx["Date"])& (cls.efx["Date"]<= cls.efxinc[-1]))]

        cls.acic = testpd.fetch("acic")
        cls.acicdates = Series([ddt(2020,12,29), ddt(2021,1,14), ddt(2021,1,15), ddt(2021,2,10)])
        cls.acic = cls.acic[~cls.acic["Date"].dt.date.isin(cls.acicdates)]

        cls.qtt = testpd.fetch("qtt")
        cls.qttdates = Series([ddt(2018,10,18), ddt(2018,11,19), ddt(2018,11,20), ddt(2018,12,6)])
        cls.qtt = cls.qtt[~cls.qtt["Date"].dt.date.isin(cls.qttdates)]


    def test_efx(self):
        sym = "efx"

        filled = self.efxdates.isin(self.efx["Date"].dt.date)
        self.assertFalse(filled.any(), f"still in there: \n{self.efxdates[filled]}")

        incompl = self.efx["Date"].dt.date.value_counts()[self.efxinc[0].date()]
        self.assertLess(incompl, 600)

        sym = self.cleaner.Prepare(sym, self.efx)
        sym = self.cleaner.FillMissingData(sym)
        self.cleaner.clear_cache(sym)

        filled = self.efxdates.isin(sym.df.index.date)
        self.assertTrue(filled.all(), f"missing: \n{self.efxdates[~filled]}")
        self.assertGreater(sym.df.shape[0], self.efx.shape[0], "new df is not larger than the old one")

        incompl = sym.df.index.to_series().dt.date.value_counts()[self.efxinc[0].date()]
        self.assertGreater(incompl, 600)

        self.assertFalse(sym.df.index.duplicated().any(), f"{sym.sym}: still something duplicated")


    def test_acic(self):
        sym = "acic"

        filled = self.acicdates.isin(self.acic["Date"].dt.date)
        self.assertFalse(filled.any(), f"still in there: \n{self.acicdates[filled]}")

        sym = self.cleaner.Prepare(sym, self.acic)
        sym = self.cleaner.FillMissingData(sym)
        self.cleaner.clear_cache(sym)

        filled = self.acicdates.isin(sym.df.index.date)
        self.assertTrue(filled.all(), f"missing: \n{self.acicdates[~filled]}")
        self.assertGreater(sym.df.shape[0], self.acic.shape[0], "new df is not larger than the old one")

        self.assertFalse(sym.df.index.duplicated().any(), f"{sym.sym}: still something duplicated")


    def test_qtt(self):
        sym = "qtt"

        filled = self.qttdates.isin(self.qtt["Date"].dt.date)
        self.assertFalse(filled.any(), f"still in there: \n{self.qttdates[filled]}")

        sym = self.cleaner.Prepare(sym, self.qtt)
        sym = self.cleaner.FillMissingData(sym)
        self.cleaner.clear_cache(sym)

        filled = self.qttdates.isin(sym.df.index.date)
        self.assertTrue(filled.all(), f"missing: \n{self.qttdates[~filled]}")
        self.assertGreater(sym.df.shape[0], self.qtt.shape[0], "new df is not larger than the old one")

        self.assertFalse(sym.df.index.duplicated().any(), f"{sym.sym}: still something duplicated")





if __name__ == "__main__":

    ut.main()
