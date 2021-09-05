from logging import getLogger, Formatter, FileHandler, INFO
from datetime import datetime as dt
FMissingDates = r"ignore\logs\Cleaner_MissingDates.log"
FErrors = r"ignore\logs\Errors.log"
FBlackList = r"ignore\logs\Blacklist.log"

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

blcklist = FileHandler(FBlackList)
blcklist.setFormatter(format_)
Blcklist = getLogger("Blcklist")
Blcklist.setLevel(INFO)
Blcklist.addHandler(blcklist)

