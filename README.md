### Pakca

To run this, you will require a running instance of the Trader Workstation of Interactive Brokers
-> https://www.interactivebrokers.com/en/trading/tws-updateable-stable.php


```python
from histdata import HistData
import datetime as dt
from time import sleep
```


```python
hd = HistData(clientId= 1)
```


```python
hd.isConnected()
```




    True



### What is the first available data according to IB?


```python
aapl = hd.getHead("aapl") # this will return a Response object
```


```python
aapl.data
```




    datetime.datetime(1980, 12, 12, 14, 30)




```python
aapl = hd.get("aapl", "1D", aapl.data, "1990-01-01")
```


```python
aapl.success
```




    True




```python
aapl.data
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>open</th>
      <th>high</th>
      <th>low</th>
      <th>close</th>
      <th>volume</th>
    </tr>
    <tr>
      <th>date</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1980-12-15</th>
      <td>0.975</td>
      <td>0.980</td>
      <td>0.975</td>
      <td>0.975</td>
      <td>219856</td>
    </tr>
    <tr>
      <th>1980-12-16</th>
      <td>0.900</td>
      <td>0.905</td>
      <td>0.900</td>
      <td>0.900</td>
      <td>132160</td>
    </tr>
    <tr>
      <th>1980-12-17</th>
      <td>0.925</td>
      <td>0.930</td>
      <td>0.925</td>
      <td>0.925</td>
      <td>108052</td>
    </tr>
    <tr>
      <th>1980-12-18</th>
      <td>0.950</td>
      <td>0.955</td>
      <td>0.950</td>
      <td>0.950</td>
      <td>91812</td>
    </tr>
    <tr>
      <th>1980-12-19</th>
      <td>1.010</td>
      <td>1.015</td>
      <td>1.010</td>
      <td>1.010</td>
      <td>60788</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>1989-12-22</th>
      <td>1.305</td>
      <td>1.330</td>
      <td>1.285</td>
      <td>1.305</td>
      <td>461468</td>
    </tr>
    <tr>
      <th>1989-12-26</th>
      <td>1.270</td>
      <td>1.315</td>
      <td>1.260</td>
      <td>1.270</td>
      <td>338212</td>
    </tr>
    <tr>
      <th>1989-12-27</th>
      <td>1.255</td>
      <td>1.275</td>
      <td>1.250</td>
      <td>1.255</td>
      <td>642516</td>
    </tr>
    <tr>
      <th>1989-12-28</th>
      <td>1.235</td>
      <td>1.260</td>
      <td>1.225</td>
      <td>1.235</td>
      <td>378140</td>
    </tr>
    <tr>
      <th>1989-12-29</th>
      <td>1.260</td>
      <td>1.275</td>
      <td>1.230</td>
      <td>1.260</td>
      <td>381024</td>
    </tr>
  </tbody>
</table>
<p>2285 rows × 5 columns</p>
</div>



##### But this does not apply to all timeframes


```python
aapl = hd.get("aapl", "1h", "1980-12-12", "1985-01-01")
```


```python
aapl.success
```




    False




```python
aapl.data
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>open</th>
      <th>high</th>
      <th>low</th>
      <th>close</th>
      <th>volume</th>
    </tr>
    <tr>
      <th>date</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
  </tbody>
</table>
</div>



### Use the .find_first method to run a binary search on the available data of a specified timeframe


```python
aapl = hd.find_first("aapl", "1h")
```


```python
aapl.data
```




    datetime.datetime(2004, 1, 26, 0, 0)




```python
aapl = hd.get("aapl", "1h", aapl.data, aapl.data + dt.timedelta(days= 180))
```


```python
aapl.success
```




    True




```python
aapl.data
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>open</th>
      <th>high</th>
      <th>low</th>
      <th>close</th>
      <th>volume</th>
    </tr>
    <tr>
      <th>date</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2004-01-26 09:00:00</th>
      <td>0.80</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.81</td>
      <td>130564</td>
    </tr>
    <tr>
      <th>2004-01-26 10:00:00</th>
      <td>0.81</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.81</td>
      <td>209300</td>
    </tr>
    <tr>
      <th>2004-01-26 11:00:00</th>
      <td>0.81</td>
      <td>0.82</td>
      <td>0.81</td>
      <td>0.81</td>
      <td>168896</td>
    </tr>
    <tr>
      <th>2004-01-26 12:00:00</th>
      <td>0.81</td>
      <td>0.82</td>
      <td>0.81</td>
      <td>0.81</td>
      <td>127764</td>
    </tr>
    <tr>
      <th>2004-01-26 13:00:00</th>
      <td>0.81</td>
      <td>0.82</td>
      <td>0.81</td>
      <td>0.82</td>
      <td>110740</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>2004-07-23 15:00:00</th>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.09</td>
      <td>1.10</td>
      <td>324828</td>
    </tr>
    <tr>
      <th>2004-07-23 16:00:00</th>
      <td>1.09</td>
      <td>1.10</td>
      <td>1.09</td>
      <td>1.10</td>
      <td>17780</td>
    </tr>
    <tr>
      <th>2004-07-23 17:00:00</th>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.09</td>
      <td>1.09</td>
      <td>1176</td>
    </tr>
    <tr>
      <th>2004-07-23 18:00:00</th>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.10</td>
      <td>56</td>
    </tr>
    <tr>
      <th>2004-07-23 19:00:00</th>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.10</td>
      <td>1.10</td>
      <td>0</td>
    </tr>
  </tbody>
</table>
<p>1433 rows × 5 columns</p>
</div>



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

hd.blocks
```




    True




```python
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
    waiting
    waiting
    received:
    




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>open</th>
      <th>high</th>
      <th>low</th>
      <th>close</th>
      <th>volume</th>
    </tr>
    <tr>
      <th>date</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2004-01-23 09:00:00</th>
      <td>0.79</td>
      <td>0.81</td>
      <td>0.79</td>
      <td>0.80</td>
      <td>124712</td>
    </tr>
    <tr>
      <th>2004-01-23 10:00:00</th>
      <td>0.80</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.81</td>
      <td>184912</td>
    </tr>
    <tr>
      <th>2004-01-23 11:00:00</th>
      <td>0.81</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.81</td>
      <td>130508</td>
    </tr>
    <tr>
      <th>2004-01-23 12:00:00</th>
      <td>0.81</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.80</td>
      <td>160804</td>
    </tr>
    <tr>
      <th>2004-01-23 13:00:00</th>
      <td>0.81</td>
      <td>0.81</td>
      <td>0.80</td>
      <td>0.80</td>
      <td>59192</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>2004-12-31 15:00:00</th>
      <td>2.31</td>
      <td>2.32</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>282212</td>
    </tr>
    <tr>
      <th>2004-12-31 16:00:00</th>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.29</td>
      <td>2.30</td>
      <td>69356</td>
    </tr>
    <tr>
      <th>2004-12-31 17:00:00</th>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>336</td>
    </tr>
    <tr>
      <th>2004-12-31 18:00:00</th>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>23184</td>
    </tr>
    <tr>
      <th>2004-12-31 19:00:00</th>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>2.30</td>
      <td>0</td>
    </tr>
  </tbody>
</table>
<p>2776 rows × 5 columns</p>
</div>



#### When requesting a lot of data, IB will throttle or even time out you requests.
#### HistData will split your requests to handle this issue.


```python
aapl.nreqs # number of requests
```




    2




```python
aapl.speed # average speed
```




    2.9005972146987915




```python
aapl.get_speeds() # speed for each request
```




    [0.1390695571899414, 5.662124872207642]




```python
aapl.get_errors() # see if there are any errors
```




    ['No Data']




```python
aapl.get_errors(withid= True)
```




    [(22, 'No Data'), (23, None)]



----
## Create a data saver


```python
from histdata import HistData
import datetime as dt
from time import sleep
from itertools import product
import logging
import sys
```


```python
handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
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
saver = Saver(clientId= 2)
```


```python
logger.setLevel(1)
```


```python
saver.block(False)
```


```python
saver.blocks
```




    False




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
