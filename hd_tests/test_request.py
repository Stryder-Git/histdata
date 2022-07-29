import pytest

from ibapi.contract import Contract
from histdata.histdata import Request
import histdata._utils as u


contract1 = Contract()
contract1.symbol = "aapl"
contract1.secType = "STK"
contract1.currency = "USD"
contract1.exchange = "SMART"

contract2 = Contract()
contract2.symbol = "nvda"
contract2.currency = "EUR"
contract2.strike = 0.1
contract2.includeExpired = True

@pytest.mark.parametrize("specs, contract", [
    ("aapl", contract1),
    ({"symbol": "aapl", "secType": "STK",
      "currency": "USD", "exchange": "SMART"}, contract1),
    (contract1, contract1),

    ({"symbol": "nvda", "currency": "EUR",
      "strike": 0.1, "includeExpired": True}, contract2)
])


def test_make_contract(specs, contract):
    calced = u.make_contract(specs)

    for att in filter(lambda x: x[0] != "_", dir(contract)):
        assert getattr(calced, att) == getattr(contract, att)


def test_make_contract_fail():
    with pytest.raises(ValueError):
        u.make_contract({"nosym": 1})

    with pytest.raises(ValueError):
        u.make_contract({"symbol": "amzn", "notvalid": 1})
