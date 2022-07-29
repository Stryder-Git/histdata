### Wrapper for InteractiveBrokers' ibapi to make requesting historical price data easier

This readme is based on examples.ipynb. To run it, you will require a running instance of the Trader Workstation of Interactive Brokers (https://www.interactivebrokers.com/en/trading/tws-updateable-stable.php)


```python
from histdata import HistData
import datetime as dt
from time import sleep
from itertools import product
import logging
import sys
```


```python
from pandas import options
options.display.notebook_repr_html = False
```


```python
hd = HistData(1)

hd.isConnected()
```




    True



### What is the first available data according to IB?


```python
aapl = hd.getHead("aapl") # this will return a Response object

first = aapl.data
first
```




    datetime.datetime(1980, 12, 12, 14, 30)




```python
aapl = hd.get("aapl", "1D", first, "1990-01-01")

aapl.success # will be true when any data has been received
```




    True




```python
aapl.data
```




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



### But this does not apply to all timeframes


```python
aapl = hd.get("aapl", "1h", first, first + dt.timedelta(days= 90))
aapl.success
```




    False




```python
aapl.data
```




    Empty DataFrame
    Columns: [open, high, low, close, volume]
    Index: []



### Use the .find_first method to run a binary search on the available data of a specified timeframe


```python
aapl = hd.find_first("aapl", "1h")

aapl.data
```




    datetime.datetime(2004, 1, 26, 0, 0)




```python
aapl = hd.get("aapl", "1h", aapl.data, aapl.data + dt.timedelta(days= 180))

aapl.success
```




    True




```python
aapl.data
```




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



---
### Up to now, HistData was in blocking mode:


```python
hd.blocks
```




    True




```python
hd.block(False)

hd.blocks
```




    False




```python
hd.block()
aapl = hd.get("aapl", "1h", "2005-01-01", "2006-01-01") # this blocks until the data is received
aapl.ready  # so this is only run when it's ready
```




    True




```python
hd.block(False)

aapl = hd.get("aapl", "1h", "2003-01-01", "2005-01-01") # now it does not block

print(aapl.ready) # and this shows you when the data has been received

while not aapl.ready:
    print("waiting")
    sleep(2)

print("received:")
aapl.data
```

    False
    waiting
    received:
    




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



#### When requesting a lot of data, IB will throttle or even time out you requests.
#### HistData will split your requests to handle this issue.


```python
aapl.nreqs # number of requests
```




    2




```python
aapl.speed # average speed
```




    0.32992684841156006




```python
aapl.get_speeds() # speed for each request
```




    [0.13506293296813965, 0.5247907638549805]




```python
aapl.get_errors() # see if there are any errors
```




    ['No Data']




```python
aapl.get_errors(withid= True)
```




    [(19, 'No Data'), (20, None)]



----
## Create a data saver
How to:

    * Inherit from HistData
    * Override the response method, which is called when a full request has been received


```python
handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
```


```python
logger.setLevel(1)
```


```python
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
```


```python
saver = Saver(2)
```


```python
saver.block(False)
```


```python
for sym, tf in product(("aapl", "amzn", "nvda"), ("1D", "30m")):
        _ = saver.get(sym, tf, "2005-01-01", "2006-01-01")
        
```

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
    


```python

```
