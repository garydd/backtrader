import pandas as pd
import numpy as np
from backtrader.feeds.pandafeed import PandasData
from backtrader.utils.py3 import filter, string_types, integer_types
import sys
sys.path.append("S:/Investment Process/Equity_Vol_Strategy/Analytics Tool/")
sys.path.append("S:/Investment Process/Equity_Vol_Strategy/Codebase/")
import DBEqVol
import QuantLib as ql
import QuantLibHelper as qh

db = DBEqVol.DBEqVol()


class EqVolFutDataFeed(PandasData):
    """
        Description pending
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
        ('open', 'PX_Open'),
        ('high', 'PX_High'),
        ('low', 'PX_Low'),
        ('close', 'PX_Last'),
        ('volume', 'PX_Volume'),
        ('openinterest', None),
        ('roll', 'Roll'),
        ('days', 'Days'),
    )

    datafields = [
        'datetime', 'open', 'high', 'low', 'close', 'volume', 'openinterest', 'roll', 'days',
    ]

    lines = ('roll', 'days')

    def __init__(self, ticker, begin=None, end=None):
        assert ticker[:2].upper() == 'UX', "Currently only support VIX futures ticker"
        if (len(ticker.split(' ')) == 2) and (begin is not None):
            ticker = db.run_query("""SELECT FUT_CUR_GEN_TICKER FROM bbg_vol_future_prices
                                    WHERE Date='{0:%Y-%m-%d}' AND Ticker='{1}'
                                    """.format(begin, ticker)).values[0][0]
        where_clause = """
                          ((Ticker='{0}') or (FUT_CUR_GEN_TICKER='{1}')) 
                       """.format(ticker, ticker.split(' ')[0])
        if begin is not None:
            where_clause += """and Date >= '{0:%Y-%m-%d}'
                            """.format(begin)
        if end is not None:
            where_clause += """and Date <= '{0:%Y-%m-%d}'
                            """.format(end)
        # print(where_clause)
        df = db.get_data('bbg_vol_future_prices', where_clause=where_clause)
        df['Roll'] = 0
        df.loc[df.index[-1], 'Roll'] = 1
        df['Days'] = list(range(df.shape[0])[::-1])
        # df.to_csv("c:/temp/df_bt_debug.csv")
        # df.loc[df.index[0], 'Roll'] = 1
        self.p.dataname = df.set_index('Date')
        self.p.name = ticker
        self._data = df.set_index('Date')
        super(EqVolFutDataFeed, self).__init__()
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
                        print(datafield)
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


class EqVolFwdVarDataFeed(PandasData):
    """
        Takes in a ticker and expiry for variance swap
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
        ('close', 'Amount'),
        ('volume', None),
        ('openinterest', None),
        ('strike', 'Strike'),
        ('n_f', 'N_f'),
        ('n_b', 'N_b'),
    )

    datafields = [
        'datetime', 'close', 'strike',
    ]

    lines = ('n_f', 'n_b', 'strike')

    def __init__(self, ticker, expiry0, expiry1, start_date, end_date, source='MSVS', variance_notional=1, country='US'):
        vsw0 = db.run_query("""SELECT Date, Amount
                            FROM index_convexity
                            WHERE Ticker='{0}' AND Type='VAR' AND ChainExpiry=1
                            AND Source = '{1}' AND Expiration='{2:%Y-%m-%d}'
                            AND Date>='{3:%Y-%m-%d}' AND Date<='{4:%Y-%m-%d}'
                            ORDER BY Date
                            """.format(ticker, source, expiry0, start_date, end_date))
        vsw1 = db.run_query("""SELECT Date, Amount
                            FROM index_convexity
                            WHERE Ticker='{0}' AND Type='VAR' AND ChainExpiry=1
                            AND Source = '{1}' AND Expiration='{2:%Y-%m-%d}'
                            AND Date>='{3:%Y-%m-%d}' AND Date<='{4:%Y-%m-%d}'
                            ORDER BY Date
                            """.format(ticker, source, expiry1, start_date, end_date))
        vsw0 = vsw0.set_index('Date').rename(columns={'Amount': 'var_f'})*100
        vsw1 = vsw1.set_index('Date').rename(columns={'Amount': 'var_b'})*100
        df = vsw0.merge(vsw1, how='inner', left_index=True, right_index=True).reset_index()
        cal = qh.get_calendar(country)
        df['N_f'] = df.apply(lambda x: cal.businessDaysBetween(qh.qdate(x['Date']), qh.qdate(expiry0)), axis=1)
        df['N_b'] = df.apply(lambda x: cal.businessDaysBetween(qh.qdate(x['Date']), qh.qdate(expiry1)), axis=1)
        df['Amount'] = df.apply(lambda x: (x['var_b']**2*x['N_b'] - x['var_f']**2*x['N_f'])/252, axis=1)
        df['Strike'] = df.apply(lambda x: np.sqrt(x['Amount']*252/(x['N_b']-x['N_f'])), axis=1)
        df.loc[:, 'Amount'] *= variance_notional
        df.set_index('Date', inplace=True)

        self.p.dataname = df.fillna(0.0)
        self.p.name = ticker.split()[0] + ' FWDVAR'
        super(EqVolFwdVarDataFeed, self).__init__()


class EqVolVSWDataFeed(PandasData):
    """
        Takes in a ticker and expiry for variance swap
        Not meant to be a tradable series
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
        ('close', 'Amount'),
        ('volume', None),
        ('openinterest', None),
    )

    datafields = [
        'datetime', 'open', 'high', 'low', 'close', 'volume', 'openinterest'
    ]

    def __init__(self, ticker, start, expiry, source='MSVS', variance_notional=1):
        where_clause = """ Ticker='{0}' and Type='VAR' and ChainExpiry=1
                       """.format(ticker)
        where_clause += """and Date = '{0:%Y-%m-%d}'
                        """.format(start)
        if source.upper() != 'SGVS':
            where_clause += """and Source = '{0}'
                            """.format(source)
        else:
            where_clause += """and (Source = '{0}' or Source is Null)
                            """.format(source)
        where_clause += """and Expiration = '{0:%Y-%m-%d}'
                        """.format(expiry)
        data = db.get_data('index_convexity', where_clause=where_clause)
        assert not data.empty, 'Query produces empty data from index_convexity, check ticker and dates'
        strike = data['Amount'][0]

        df = db.run_query("""SELECT [Date], [PX_Last] 
                            FROM bbg_historical_prices 
                            WHERE Date >= '{0:%Y-%m-%d}'
                            AND Date <= '{1:%Y-%m-%d}'
                            AND Ticker = '{2}'
                         """.format(start, expiry, ticker))
        assert not df.empty, 'Query produces empty data from bbg_historical_prices, check ticker and dates'

        df.set_index('Date', inplace=True)
        df['LogReturnSq'] = np.log(df['PX_Last']/df['PX_Last'].shift(1))**2
        df['Amount'] = (df['LogReturnSq'] * 252 - strike**2)/(len(df)-1) * 100**2 * variance_notional
        self.p.dataname = df.fillna(0.0)
        self.p.name = ticker
        self.strike = strike
        super(EqVolVSWDataFeed, self).__init__()

