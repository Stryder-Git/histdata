from logging import getLogger, Formatter, FileHandler, INFO
from datetime import datetime as dt
FMissingDates = r"C:\Users\User\Desktop\Python\TradeCode\TWS_SPY_Data\ignore\CleanerLogs\MissingDates.log"
FErrors = r"C:\Users\User\Desktop\Python\TradeCode\TWS_SPY_Data\ignore\CleanerLogs\Errors.log"

time = dt.strftime(dt.now(), "%Y-%m-%d %H:%M")
format_ = Formatter(f"%(name)s: {time}\n%(message)s")

mdhandler = FileHandler(FMissingDates)
mdhandler.setFormatter(format_)
#   Logger for Missing Dates
MissingDates = getLogger("MissingDates")
MissingDates.setLevel(INFO)
MissingDates.addHandler(mdhandler)

errhandler = FileHandler(FErrors)
errhandler.setFormatter(format_)
Errors = getLogger("Errors")
Errors.setLevel(INFO)
Errors.addHandler(errhandler)

