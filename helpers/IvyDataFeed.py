import pandas as pd
from backtrader.feeds.pandafeed import PandasData
from backtrader.utils.py3 import filter, string_types, integer_types
import sys
sys.path.append("S:/Investment Process/Equity_Vol_Strategy/Analytics Tool/")
import DBIvy

db = DBIvy.DBIvy()


class IvyDataFeed(PandasData):
    """
    Takes in a ticker
    """

    params = (
        ('nocase', True),

        # Possible values for datetime (must always be present)
        #  None : datetime is the "index" in the Pandas Dataframe
        #  -1 : autodetect position or case-wise equal name
        #  >= 0 : numeric index to the colum in the pandas dataframe
        #  string : column name (as index) in the pandas dataframe
        ('datetime', None),

        # Possible values below:
        #  None : column not present
        #  -1 : autodetect position or case-wise equal name
        #  >= 0 : numeric index to the colum in the pandas dataframe
        #  string : column name (as index) in the pandas dataframe
        ('open', 'OpenPrice'),
        ('high', 'AskHigh'),
        ('low', 'BidLow'),
        ('close', 'ClosePrice'),
        ('volume', 'Volume'),
        ('openinterest', None),
    )

    datafields = [
        'datetime', 'open', 'high', 'low', 'close', 'volume', 'openinterest'
    ]

    def __init__(self, ticker, begin=None, end=None):
        df = db.get_hist_price(ticker, begin=begin, end=end, adjusted=True)
        self._data = df
        self.p.dataname = df
        self.p.name = ticker
        super(IvyDataFeed, self).__init__()


class IvyOptionDataFeed(PandasData):
    """
    Takes in a ticker, for options
    """
    params = (
        ('nocase', True),

        # Possible values for datetime (must always be present)
        #  None : datetime is the "index" in the Pandas Dataframe
        #  -1 : autodetect position or case-wise equal name
        #  >= 0 : numeric index to the colum in the pandas dataframe
        #  string : column name (as index) in the pandas dataframe
        ('datetime', None),

        # Possible values below:
        #  None : column not present
        #  -1 : autodetect position or case-wise equal name
        #  >= 0 : numeric index to the colum in the pandas dataframe
        #  string : column name (as index) in the pandas dataframe
        ('open', None),
        ('high', None),
        ('low', None),
        ('close', 'Mid'),
        ('volume', 'Volume'),
        ('openinterest', 'OpenInterest'),
        ('ivol', 'ImpliedVolatility'),
        ('delta', 'Delta'),
        ('gamma', 'Gamma'),
        ('vega', 'Vega'),
        ('theta', 'Theta')
    )

    datafields = [
        'datetime', 'open', 'high', 'low', 'close', 'volume', 'openinterest',
        'ivol', 'delta', 'gamma', 'vega', 'theta'
    ]

    lines = (('delta'),)

    def __init__(self, symbol, begin=None, end=None):
        df = db.get_hist_opt_by_symbol(symbol, begin=begin, end=end)
        self._data = df
        self.p.dataname = df
        self.p.name = symbol
        super(IvyOptionDataFeed, self).__init__()
        # these "colnames" can be strings or numeric types
        colnames = list(self.p.dataname.columns.values)
        if self.p.datetime is None:
            # datetime is expected as index col and hence not returned
            pass

        # try to autodetect if all columns are numeric
        cstrings = filter(lambda x: isinstance(x, string_types), colnames)
        colsnumeric = not len(list(cstrings))

        # Where each datafield find its value
        self._colmapping = dict()

        # Build the column mappings to internal fields in advance
        for datafield in set(self.getlinealiases() + tuple(self.datafields)):
            defmapping = getattr(self.params, datafield)

            if isinstance(defmapping, integer_types) and defmapping < 0:
                # autodetection requested
                for colname in colnames:
                    if isinstance(colname, string_types):
                        if self.p.nocase:
                            found = datafield.lower() == colname.lower()
                        else:
                            found = datafield == colname

                        if found:
                            self._colmapping[datafield] = colname
                            break

                if datafield not in self._colmapping:
                    # autodetection requested and not found
                    self._colmapping[datafield] = None
                    continue
            else:
                # all other cases -- used given index
                self._colmapping[datafield] = defmapping

