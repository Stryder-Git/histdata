import pandas as pd
from ibapi.contract import Contract

ibtfs = {pd.Timedelta(1, unit="s"): "1 secs",
         pd.Timedelta(5, unit="s"): "5 secs",
         pd.Timedelta(10, unit="s"): "10 secs",
         pd.Timedelta(15, unit="s"): "15 secs",
         pd.Timedelta(30, unit="s"): "30 secs",
         pd.Timedelta(1, unit="m"): "1 min",
         pd.Timedelta(2, unit="m"): "2 mins",
         pd.Timedelta(3, unit="m"): "3 mins",
         pd.Timedelta(5, unit="m"): "5 mins",
         pd.Timedelta(10, unit="m"): "10 mins",
         pd.Timedelta(15, unit="m"): "15 mins",
         pd.Timedelta(20, unit="m"): "20 mins",
         pd.Timedelta(30, unit="m"): "30 mins",
         pd.Timedelta(1, unit="h"): "1 hour",
         pd.Timedelta(2, unit="h"): "2 hours",
         pd.Timedelta(3, unit="h"): "3 hours",
         pd.Timedelta(4, unit="h"): "4 hours",
         pd.Timedelta(8, unit="h"): "8 hours",
         pd.Timedelta(1, unit="D"): "1 day",
         pd.Timedelta(1, unit="W"): "1W",
         pd.Timedelta(30, unit="D"): "1M"}


class NotValid: pass

def make_contract(symbol):
    if isinstance(symbol, Contract): return symbol

    contract = Contract()

    if isinstance(symbol, dict):
        try: contract.symbol = symbol["symbol"]
        except KeyError as e:
            raise ValueError("You need a symbol in the contract dictionary") from e

        for att, value in symbol.items():
            if getattr(contract, att, NotValid) is NotValid:
                raise ValueError(f"{att} is not a valid attribute for a Contract")

            setattr(contract, att, value)
        return contract

    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract