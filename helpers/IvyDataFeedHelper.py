import datetime
import pandas as pd
from backtrader.feeds.pandafeed import PandasData
from backtrader.utils.py3 import filter, string_types, integer_types
import sys
sys.path.append("S:/Investment Process/Equity_Vol_Strategy/Analytics Tool/")
import DBIvy

db = DBIvy.DBIvy()

def opt_symbol_lookup(ticker, date, delta=None, strike=None, strike_mode=None, callput=None, expiry=None, tenor=None):
    """
    Find the option symbol that is the closest match for the supplied criteria

    :param ticker: underlying ticker
    :param date: reference date
    :param delta: option delta, e.g. -0.5 for 50% delta put
    :param strike: desired option strike, depends on strike_mode e.g. 175 (spot), 100% (spot, forward)
    :param strike_mode: absolute, spot, forward
    :param callput: call or put
    :param expiry: desired expiration date
    :param tenor: desired tenor
    :return: option symbol in IvyDB format
    """
    pass