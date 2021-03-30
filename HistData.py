from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from threading import Thread
from Cleaner.mylogging import Errors
from Request import Request_Manager
from Cleaner.Cleaner import Cleaner

class HistData(EWrapper, EClient):
    ErrResponses = ["No Data", "invalid symbol", "No head time stamp", "timed out"]

    def __init__(self, clientid= 99999):
        EClient.__init__(self, self)
        self.connect('127.0.0.1', 7497, clientid)
        Thread(target= self.run, daemon= True).start()
        self.R = Request_Manager()
        self.errors = Errors
        self.Block = True
        self.IBTWSConnected = False
        self.ImmediatelyCleanData = False
        self.Cleaner = Cleaner(self)

    def nextValidId(self, id_): print("connected"); self.IBTWSConnected = True
    def error(self, id_, code, string):
        self.errors.info(f"{id_} {code} {self.R.tf_sym(id_)[1]}\n{string}")
        print(f"{id_} {code}\n{string}")

        if id_ == -1:
            if "Connectivity between IB and Trader Workstation has been lost" in string:
                self.IBTWSConnected = False
            elif "Connectivity between IB and Trader Workstation has been restored" in string:
                self.IBTWSConnected = True

        if "query returned no data" in string:
            self.historicalDataEnd(id_, code, "No Data")

        elif "No head time stamp" in string:
            self.headTimestamp(id_, "No head time stamp")

        elif "No security definition" in string or "is ambiguous" in string:
            if not self.IBTWSConnected: return
            if self.R.ishistdatareq(id_): self.historicalDataEnd(id_, code, "invalid symbol")
            else: self.headTimestamp(id_, "invalid symbol")

        elif "Request Timed Out" in string:
            if self.R.ishistdatareq(id_): self.historicalDataEnd(id_, code, "timed out")
            else: self.headTimestamp(id_, "timed out")

        elif "Couldn't connect to TWS" in string or "Not connected" in string: exit()

    def headTimestamp(self, id_, stamp):
        resp = self.R.receiveStamp(id_, stamp, err= stamp in self.ErrResponses or None)
        if not resp is None: self.response(resp)

    def historicalData(self, id_, bar): self.R.add(id_, bar)

    def historicalDataEnd(self, id_, start, end):
        response = self.R.end(id_, end if end in self.ErrResponses else None)
        if not response is None: self.response(response)


    def get(self, symbol, timeframe, start, end, format_= 1, onlyRTH= False,
            type_= "TRADES", setDateasIndex= True, transmit= None):
        if transmit is None: transmit = self
        if self.Block or not transmit:
            res = self.R.makeRequest(symbol, timeframe, start, end, format_,
                                      onlyRTH, type_,setDateasIndex, transmit)

            if self.ImmediatelyCleanData and self.R.isResponse(res):
                res = self.CleanResponse(res)
            return res
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

    def setImmediatelyCleanTo(self, clean): self.ImmediatelyCleanData = clean

    def CleanResponse(self, res, clear_cache= True):
        to_clean = self.Cleaner.Prepare(res.sym, res.data)
        to_clean = self.Cleaner.FillMissingData(to_clean)
        if clear_cache: self.Cleaner.clear_cache(to_clean)
        res.data = to_clean.df
        return res

    def response(self, response):
        """ overwrite in child class """
        if not self.R.directreturn:
            print(response.tf, response.sym)
            print(response.df)
            pass