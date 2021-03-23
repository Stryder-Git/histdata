from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from threading import Thread
from Cleaner.mylogging import Errors
from Request import Request_Manager

class HistData(EWrapper, EClient):
    ErrResponses = ["No Data", "invalid symbol", "No head time stamp"]

    def __init__(self, clientid= 99999):
        EClient.__init__(self, self)
        self.connect('127.0.0.1', 7497, clientid)
        Thread(target= self.run, daemon= True).start()
        self.R = Request_Manager()
        self.data = {}
        self.errors = Errors
        self.Block = True

    def nextValidId(self, id_): print("connected")
    def error(self, id_, code, string):
        self.errors.info(f"{id_} {code} {self.R.tf_sym(id_)[1]}"
                         f"\n{string}")
        if id_ != -1: print(f"{id_} {code}\n{string}")

        if "query returned no data" in string:
            self.historicalDataEnd(id_, code, "No Data")

        elif "No security definition" in string or \
            "is ambiguous" in string:
            if self.R.ishistdatareq(id_):
                self.historicalDataEnd(id_, code, "invalid symbol")
            else:
                self.headTimestamp(id_, "invalid symbol")

        elif "No head time stamp" in string:
            self.headTimestamp(id_, "No head time stamp")

        elif "Couldn't connect to TWS" in string or \
            "Not connected" in string:
            exit()

    def headTimestamp(self, id_, stamp):
        stamp, sym = self.R.receiveStamp(id_, stamp)
        if stamp is not None: self.response("stamp", sym, stamp)

    def historicalData(self, id_, bar): self.R.add(id_, bar)


    def historicalDataEnd(self, id_, start, end):
        df = self.R.end(id_)
        if df is not None:
            if end in ["invalid symbol", "timed out"]:
                self.response(*self.R.tf_sym(id_), end)
                self.R.markasfailed(id_)
            else:
                self.response(*self.R.tf_sym(id_), df)


    def get(self, symbol, timeframe, start, end= None, format_= 1, onlyRTH= False,
            type_= "TRADES", setDateasIndex= True, transmit= None):
        if transmit is None: transmit = self
        if self.Block or not transmit:
            return self.R.makeRequest(symbol, timeframe, start, end, format_,
                                      onlyRTH, type_,setDateasIndex, transmit)
        else:
            Thread(target= self.R.makeRequest,
                   args= [symbol, timeframe, start, end, format_,
                          onlyRTH, type_, setDateasIndex, transmit]).start()

    def getHead(self, symbol, type_= "TRADES", onlyRTH= False, format_= 1, transmit= None):
        if transmit is None: transmit = self
        return self.R.getHeadTimeStamp(symbol, type_, onlyRTH, format_, transmit)

    def NotBlocking(self):
        self.Block = False
        self.R.directreturn = False

    def Blocking(self, directreturn= True):
        self.Block = True
        self.R.directreturn = directreturn

    def response(self, tf, sym, df):
        """ overwrite in child class """
        if not self.R.directreturn:
            print(tf, sym)
            print(df)
            pass