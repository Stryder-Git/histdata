from HistData import HistData
hd = HistData(34312213)
from datetime import datetime as dt
from time import sleep

resp = hd.get("aapl", "1m", dt(2021,3,18), dt.now())

print(resp.speed, resp.errors)

print(hd.R.TIMEOUT, id(hd.R.TIMEOUT), id(hd.R),"\n")
hd.R.setTimeOut(0.0001)
print(hd.R.TIMEOUT, id(hd.R.TIMEOUT), id(hd.R),"\n")

resp = hd.get("aapl", "1m", dt(2021,3,18), dt.now())
print(resp.speed, resp.errors)
print(hd.R.BLACKLIST)
sleep(150)
hd.disconnect()
exit()