Wrapper for InteractiveBrokers’ ibapi to make requesting historical price data easier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This readme is based on examples.ipynb. To run it, you will require a
running instance of the Trader Workstation of Interactive Brokers
(https://www.interactivebrokers.com/en/trading/tws-updateable-stable.php)

.. code:: ipython3

    from histdata import HistData
    import datetime as dt
    from time import sleep
    from itertools import product
    import logging
    import sys

.. code:: ipython3

    from pandas import options
    options.display.notebook_repr_html = False

.. code:: ipython3

    hd = HistData(1)
    
    hd.isConnected()




.. parsed-literal::

    True



What is the first available data according to IB?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: ipython3

    aapl = hd.getHead("aapl") # this will return a Response object
    
    first = aapl.data
    first




.. parsed-literal::

    datetime.datetime(1980, 12, 12, 14, 30)



.. code:: ipython3

    aapl = hd.get("aapl", "1D", first, "1990-01-01")
    
    aapl.success # will be true when any data has been received




.. parsed-literal::

    True



.. code:: ipython3

    aapl.data




.. parsed-literal::

                 open   high    low  close  volume
    date                                          
    1980-12-15  0.975  0.980  0.975  0.975  219856
    1980-12-16  0.900  0.905  0.900  0.900  132160
    1980-12-17  0.925  0.930  0.925  0.925  108052
    1980-12-18  0.950  0.955  0.950  0.950   91812
    1980-12-19  1.010  1.015  1.010  1.010   60788
    ...           ...    ...    ...    ...     ...
    1989-12-22  1.305  1.330  1.285  1.305  461468
    1989-12-26  1.270  1.315  1.260  1.270  338212
    1989-12-27  1.255  1.275  1.250  1.255  642516
    1989-12-28  1.235  1.260  1.225  1.235  378140
    1989-12-29  1.260  1.275  1.230  1.260  381024
    
    [2285 rows x 5 columns]



But this does not apply to all timeframes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: ipython3

    aapl = hd.get("aapl", "1h", first, first + dt.timedelta(days= 90))
    aapl.success




.. parsed-literal::

    False



.. code:: ipython3

    aapl.data




.. parsed-literal::

    Empty DataFrame
    Columns: [open, high, low, close, volume]
    Index: []



Use the .find_first method to run a binary search on the available data of a specified timeframe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: ipython3

    aapl = hd.find_first("aapl", "1h")
    
    aapl.data




.. parsed-literal::

    datetime.datetime(2004, 1, 26, 0, 0)



.. code:: ipython3

    aapl = hd.get("aapl", "1h", aapl.data, aapl.data + dt.timedelta(days= 180))
    
    aapl.success




.. parsed-literal::

    True



.. code:: ipython3

    aapl.data




.. parsed-literal::

                         open  high   low  close  volume
    date                                                
    2004-01-26 09:00:00  0.80  0.81  0.80   0.81  130564
    2004-01-26 10:00:00  0.81  0.81  0.80   0.81  209300
    2004-01-26 11:00:00  0.81  0.82  0.81   0.81  168896
    2004-01-26 12:00:00  0.81  0.82  0.81   0.81  127764
    2004-01-26 13:00:00  0.81  0.82  0.81   0.82  110740
    ...                   ...   ...   ...    ...     ...
    2004-07-23 15:00:00  1.10  1.10  1.09   1.10  324828
    2004-07-23 16:00:00  1.09  1.10  1.09   1.10   17780
    2004-07-23 17:00:00  1.10  1.10  1.09   1.09    1176
    2004-07-23 18:00:00  1.10  1.10  1.10   1.10      56
    2004-07-23 19:00:00  1.10  1.10  1.10   1.10       0
    
    [1433 rows x 5 columns]



--------------

Up to now, HistData was in blocking mode:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: ipython3

    hd.blocks




.. parsed-literal::

    True



.. code:: ipython3

    hd.block(False)
    
    hd.blocks




.. parsed-literal::

    False



.. code:: ipython3

    hd.block()
    aapl = hd.get("aapl", "1h", "2005-01-01", "2006-01-01") # this blocks until the data is received
    aapl.ready  # so this is only run when it's ready




.. parsed-literal::

    True



.. code:: ipython3

    hd.block(False)
    
    aapl = hd.get("aapl", "1h", "2003-01-01", "2005-01-01") # now it does not block
    
    print(aapl.ready) # and this shows you when the data has been received
    
    while not aapl.ready:
        print("waiting")
        sleep(2)
    
    print("received:")
    aapl.data


.. parsed-literal::

    False
    waiting
    received:
    



.. parsed-literal::

                         open  high   low  close  volume
    date                                                
    2004-01-23 09:00:00  0.79  0.81  0.79   0.80  124712
    2004-01-23 10:00:00  0.80  0.81  0.80   0.81  184912
    2004-01-23 11:00:00  0.81  0.81  0.80   0.81  130508
    2004-01-23 12:00:00  0.81  0.81  0.80   0.80  160804
    2004-01-23 13:00:00  0.81  0.81  0.80   0.80   59192
    ...                   ...   ...   ...    ...     ...
    2004-12-31 15:00:00  2.31  2.32  2.30   2.30  282212
    2004-12-31 16:00:00  2.30  2.30  2.29   2.30   69356
    2004-12-31 17:00:00  2.30  2.30  2.30   2.30     336
    2004-12-31 18:00:00  2.30  2.30  2.30   2.30   23184
    2004-12-31 19:00:00  2.30  2.30  2.30   2.30       0
    
    [2776 rows x 5 columns]



When requesting a lot of data, IB will throttle or even time out you requests.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

HistData will split your requests to handle this issue.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: ipython3

    aapl.nreqs # number of requests




.. parsed-literal::

    2



.. code:: ipython3

    aapl.speed # average speed




.. parsed-literal::

    0.32992684841156006



.. code:: ipython3

    aapl.get_speeds() # speed for each request




.. parsed-literal::

    [0.13506293296813965, 0.5247907638549805]



.. code:: ipython3

    aapl.get_errors() # see if there are any errors




.. parsed-literal::

    ['No Data']



.. code:: ipython3

    aapl.get_errors(withid= True)




.. parsed-literal::

    [(19, 'No Data'), (20, None)]



--------------

Create a data saver
-------------------

How to:

::

   * Inherit from HistData
   * Override the response method, which is called when a full request has been received

.. code:: ipython3

    handler = logging.StreamHandler(sys.stdout)
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)

.. code:: ipython3

    logger.setLevel(1)

.. code:: ipython3

    class Saver(HistData):
        def get(self, *args, **kwargs):
            logger.info("requesting %s %s", *args[:2])
            return super().get(*args, **kwargs)
        
        def _fn(self, r): 
            s = str(r.start).split(" ")[0]
            e = str(r.end).split(" ")[0]
            return f"{r.sym}_{r.tf}_{s}_{e}.csv"
        
        def response(self, r):
            logger.info("received %s %s", r.sym, r.tf)
            if r:
                fn = self._fn(r)
                r.data.to_csv(fn)
                logger.info("saved %s", fn)
            else:
                logger.info("no data available: %s", r.errors)

.. code:: ipython3

    saver = Saver(2)

.. code:: ipython3

    saver.block(False)

.. code:: ipython3

    for sym, tf in product(("aapl", "amzn", "nvda"), ("1D", "30m")):
            _ = saver.get(sym, tf, "2005-01-01", "2006-01-01")
            


.. parsed-literal::

    requesting aapl 1D
    requesting aapl 30m
    requesting amzn 1D
    requesting amzn 30m
    requesting nvda 1D
    requesting nvda 30m
    received aapl 1D
    saved aapl_1D_2005-01-03_2005-12-30.csv
    received amzn 1D
    saved amzn_1D_2005-01-03_2005-12-30.csv
    received nvda 1D
    saved nvda_1D_2005-01-03_2005-12-30.csv
    received nvda 30m
    saved nvda_30m_2005-01-03_2005-12-30.csv
    received amzn 30m
    saved amzn_30m_2005-01-03_2005-12-30.csv
    received aapl 30m
    saved aapl_30m_2005-01-03_2005-12-30.csv
    

