# --------------------------------------- IMPORT LIBRARIES -------------------------------------------
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import random
import math
import quandl
import warnings
import time
warnings.filterwarnings("ignore")

from feature_select import FeatureSelector

from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import Normalizer
from sklearn.preprocessing import MinMaxScaler
import talib as tb

# --------------------------------------- GLOBAL PARAMETERS -------------------------------------------


# Set total fund pool
TRAIN_PORTION = 0.9
ACCOUNT_FUND = 100000
ALLOCATION_RATIO = 0.2
SINGLE_TRADING_FUND = ACCOUNT_FUND * ALLOCATION_RATIO
PRICE_IMPACT = 0.1

# Start and end period of historical data in question
START_TRAIN = datetime(2000, 1, 1)
END_TRAIN = datetime(2017, 2, 12)
START_TEST = datetime(2017, 2, 12)
END_TEST = datetime(2019, 2, 22)

# DJIA component stocks
DJI = ['MMM', 'AXP', 'AAPL', 'BA', 'CAT', 'CVX', 'CSCO', 'KO', 'DIS', 'XOM', 'GE', 'GS',
          'HD', 'IBM', 'INTC', 'JNJ', 'JPM', 'MCD', 'MRK', 'MSFT', 'NKE', 'PFE', 'PG', 'UTX',
          'UNH', 'VZ', 'WMT']
DJI_N = ['3M','American Express', 'Apple','Boeing','Caterpillar','Chevron','Cisco Systems','Coca-Cola','Disney'
         ,'ExxonMobil','General Electric','Goldman Sachs','Home Depot','IBM','Intel','Johnson & Johnson',
         'JPMorgan Chase','McDonalds','Merck','Microsoft','NIKE','Pfizer','Procter & Gamble',
         'United Technologies','UnitedHealth Group','Verizon Communications','Wal Mart']

CONTEXT_DATA = ['^GSPC', '^DJI', '^IXIC', '^RUT', 'SPY', 'QQQ', '^VIX', 'GLD', '^TYX', '^TNX' , 'SHY', 'SHV']

CONTEXT_DATA_N = ['S&P 500', 'Dow Jones Industrial Average', 'NASDAQ Composite', 'Russell 2000', 'SPDR S&P 500 ETF',
 'Invesco QQQ Trust', 'CBOE Volatility Index', 'SPDR Gold Shares', 'Treasury Yield 30 Years',
 'CBOE Interest Rate 10 Year T Note', 'iShares 1-3 Year Treasury Bond ETF', 'iShares Short Treasury Bond ETF']

random.seed(633)
RANDOM_STOCK = random.sample(DJI, 1)
ADD_STOCKS = 4

#13 WEEK TREASURY BILL (^IRX)
# https://finance.yahoo.com/quote/%5EIRX?p=^IRX&.tsrc=fin-srch
RISK_FREE_RATE = ((1+0.02383)**(1.0/252))-1 # Assuming 1.43% risk free rate divided by 360 to get the daily risk free rate.
MAR = 0.05
# ------------------------------------------------ CLASSES --------------------------------------------

class DataRetrieval:
    """
    This class prepares data by downloading historical data from pre-saved data.
    """

    def __init__(self):
        # Initiate component data downloads
        self._dji_components_data()

    def _get_daily_data(self, symbol):
        """
        This class prepares data by downloading historical data from Yahoo Finance,

        """
        daily_price = pd.read_csv("{}{}{}".format('./data/', symbol, '.csv'), index_col='Date', parse_dates=True)

        return daily_price

    def _dji_components_data(self):
        """
        This function download all components data and assembles the required OHLCV data into respective data
        """

        for i in DJI + CONTEXT_DATA:
            print("Downloading {}'s historical data".format((DJI + CONTEXT_DATA_N)[(DJI + CONTEXT_DATA).index(i)]))
            daily_price = self._get_daily_data(i)
            if i == (DJI + CONTEXT_DATA)[0]:
                self.components_df_o = pd.DataFrame(index=daily_price.index, columns=(DJI + CONTEXT_DATA))
                self.components_df_c = pd.DataFrame(index=daily_price.index, columns=(DJI + CONTEXT_DATA))
                self.components_df_h = pd.DataFrame(index=daily_price.index, columns=(DJI + CONTEXT_DATA))
                self.components_df_l = pd.DataFrame(index=daily_price.index, columns=(DJI + CONTEXT_DATA))
                self.components_df_v = pd.DataFrame(index=daily_price.index, columns=(DJI + CONTEXT_DATA))
                # Since this span more than 10 years of data, many corporate actions could have happened,
                # adjusted closing price is used instead
                self.components_df_o[i] = daily_price["Open"]
                self.components_df_c[i] = daily_price["Adj Close"]
                self.components_df_h[i] = daily_price["High"]
                self.components_df_l[i] = daily_price["Low"]
                self.components_df_v[i] = daily_price["Volume"]
            else:
                self.components_df_o[i] = daily_price["Open"]
                self.components_df_c[i] = daily_price["Adj Close"]
                self.components_df_h[i] = daily_price["High"]
                self.components_df_l[i] = daily_price["Low"]
                self.components_df_v[i] = daily_price["Volume"]

    def get_dailyprice_df(self):
        self.dow_stocks_test = self.components_df_c.loc[START_TEST:END_TEST][DJI]
        self.dow_stocks_train = self.components_df_c.loc[START_TRAIN:END_TRAIN][DJI]

    def get_all(self):
        self.get_dailyprice_df()
        return self.dow_stocks_train, self.dow_stocks_test

    def technical_indicators_df(self, daily_data):
        o = daily_data['Open'].values
        c = daily_data['Close'].values
        h = daily_data['High'].values
        l = daily_data['Low'].values
        v = daily_data['Volume'].astype(float).values
        # define the technical analysis matrix

        # Most data series are normalized by their series' mean
        ta = pd.DataFrame()
        ta['MA5'] = tb.MA(c, timeperiod=5) / tb.MA(c, timeperiod=5).mean()
        ta['MA10'] = tb.MA(c, timeperiod=10) / tb.MA(c, timeperiod=10).mean()
        ta['MA20'] = tb.MA(c, timeperiod=20) / tb.MA(c, timeperiod=20).mean()
        ta['MA60'] = tb.MA(c, timeperiod=60) / tb.MA(c, timeperiod=60).mean()
        ta['MA120'] = tb.MA(c, timeperiod=120) / tb.MA(c, timeperiod=120).mean()
        ta['MA5'] = tb.MA(v, timeperiod=5) / tb.MA(v, timeperiod=5).mean()
        ta['MA10'] = tb.MA(v, timeperiod=10) / tb.MA(v, timeperiod=10).mean()
        ta['MA20'] = tb.MA(v, timeperiod=20) / tb.MA(v, timeperiod=20).mean()
        ta['ADX'] = tb.ADX(h, l, c, timeperiod=14) / tb.ADX(h, l, c, timeperiod=14).mean()
        ta['ADXR'] = tb.ADXR(h, l, c, timeperiod=14) / tb.ADXR(h, l, c, timeperiod=14).mean()
        ta['MACD'] = tb.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)[0] / \
                     tb.MACD(c, fastperiod=12, slowperiod=26, signalperiod=9)[0].mean()
        ta['RSI'] = tb.RSI(c, timeperiod=14) / tb.RSI(c, timeperiod=14).mean()
        ta['BBANDS_U'] = tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[0] / \
                         tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[0].mean()
        ta['BBANDS_M'] = tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[1] / \
                         tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[1].mean()
        ta['BBANDS_L'] = tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[2] / \
                         tb.BBANDS(c, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0)[2].mean()
        ta['AD'] = tb.AD(h, l, c, v) / tb.AD(h, l, c, v).mean()
        ta['ATR'] = tb.ATR(h, l, c, timeperiod=14) / tb.ATR(h, l, c, timeperiod=14).mean()
        ta['HT_DC'] = tb.HT_DCPERIOD(c) / tb.HT_DCPERIOD(c).mean()
        ta["High/Open"] = h / o
        ta["Low/Open"] = l / o
        ta["Close/Open"] = c / o

        self.ta = ta

    def label(self, df, seq_length):
        return (df['Returns'] > 0).astype(int)

    def preprocessing(self, symbol):
        print("\n")
        print("Preprocessing {} & its technical data".format(symbol))
        print("============================================")
        self.daily_data = pd.DataFrame()
        self.daily_data['Returns'] = pd.Series(
            (self.components_df_c[symbol] / self.components_df_c[symbol].shift(1) - 1) * 100,
            index=self.components_df_c[symbol].index)
        self.daily_data['Open'] = self.components_df_o[symbol]
        self.daily_data['Close'] = self.components_df_c[symbol]
        self.daily_data['High'] = self.components_df_h[symbol]
        self.daily_data['Low'] = self.components_df_l[symbol]
        self.daily_data['Volume'] = self.components_df_v[symbol].astype(float)
        seq_length = 3
        self.technical_indicators_df(self.daily_data)
        self.X = self.daily_data[['Open', 'Close', 'High', 'Low', 'Volume']] / self.daily_data[
            ['Open', 'Close', 'High', 'Low', 'Volume']].mean()
        self.y = self.label(self.daily_data, seq_length)
        X_shift = [self.X]

        for i in range(1, seq_length):
            shifted_df = self.daily_data[['Open', 'Close', 'High', 'Low', 'Volume']].shift(i)
            X_shift.append(shifted_df / shifted_df.mean())
        ohlc = pd.concat(X_shift, axis=1)
        ohlc.columns = sum([[c + 'T-{}'.format(i) for c in ['Open', 'Close', 'High', 'Low', 'Volume']] \
                            for i in range(seq_length)], [])
        self.ta.index = ohlc.index
        self.X = pd.concat([ohlc, self.ta], axis=1)
        self.Xy = pd.concat([self.X, self.y], axis=1)

        fs = FeatureSelector(data=self.X, labels=self.y)
        fs.identify_all(selection_params={'missing_threshold': 0.6,
                                          'correlation_threshold': 0.9,
                                          'task': 'regression',
                                          'eval_metric': 'auc',
                                          'cumulative_importance': 0.99})
        self.X_fs = fs.remove(methods='all', keep_one_hot=True)
        return self.X_fs

    def get_feature_dataframe(self, selected_stock):
        self.feature_df = pd.DataFrame()
        for s in selected_stock:
            if s == selected_stock[0]:
                df = self.preprocessing(s)
                df.columns = [str(s) + '_' + str(col) for col in df.columns]
                self.feature_df = df
            else:
                df = self.preprocessing(s)
                df.columns = [str(s) + '_' + str(col) for col in df.columns]
                self.feature_df = pd.concat([self.feature_df, df], axis=1)
        return self.feature_df


class MathCalc:
    """
    This class performs all the mathematical calculations
    """

    @staticmethod
    def calc_return(period):
        """
        This function compute the return of a series
        """
        period_return = period / period.shift(1) - 1
        return period_return[1:len(period_return)]

    @staticmethod
    def calc_monthly_return(series):
        """
        This function computes the monthly return

        """
        return MathCalc.calc_return(series.resample('M').last())

    @staticmethod
    def positive_pct(series):
        """
        This function calculate the probably of positive values from a series of values.
        :param series:
        :return:
        """
        return (float(len(series[series > 0])) / float(len(series)))*100

    @staticmethod
    def calc_yearly_return(series):
        """
        This function computes the yearly return

        """
        return MathCalc.calc_return(series.resample('AS').last())

    @staticmethod
    def max_drawdown(r):
        """
        This function calculates maximum drawdown occurs in a series of cummulative returns
        """
        dd = r.div(r.cummax()).sub(1)
        maxdd = dd.min()
        return round(maxdd, 2)

    @staticmethod
    def calc_lake_ratio(series):

        """
        This function computes lake ratio

        """
        water = 0
        earth = 0
        series = series.dropna()
        water_level = []
        for i, s in enumerate(series):
            if i == 0:
                peak = s
            else:
                peak = np.max(series[0:i])
            water_level.append(peak)
            if s < peak:
                water = water + peak - s
            earth = earth + s
        return water / earth

    @staticmethod
    def calc_gain_to_pain(returns):
        """
        This function computes the gain to pain ratio given a series of profits and losees

        """
        profit_loss = np.array(returns)
        sum_returns = returns.sum()
        sum_neg_months = abs(returns[returns < 0].sum())
        gain_to_pain = sum_returns / sum_neg_months

        # print "Gain to Pain ratio: ", gain_to_pain
        return gain_to_pain

    @staticmethod
    def sharpe_ratio(returns):
        return ((returns.mean() - RISK_FREE_RATE) / returns.std()) * np.sqrt(252)

    @staticmethod
    def downside_deviation(returns, mar, order):
        # This method returns a lower partial moment of the returns
        # Create an array he same length as returns containing the minimum return threshold
        threshold_array = np.empty(len(returns))
        threshold_array.fill(mar)
        # Calculate the difference between the threshold and the returns
        diff = threshold_array - returns
        diff = np.clip(diff, a_min=0.0, a_max=None)

        # Return the sum of the different to the power of order
        return np.sum(diff ** order) / len(returns)

    @staticmethod
    def sortino_ratio(returns):
        return ((returns.mean() - RISK_FREE_RATE) / math.sqrt(MathCalc.downside_deviation(returns, MAR, 2)))* np.sqrt(252)

    @staticmethod
    def calc_kpi(portfolio):
        """
        This function calculates individual portfolio KPI related its risk profile
        """

        kpi = pd.DataFrame(index=['KPI'], columns=['Avg. monthly return', 'Pos months pct', 'Avg yearly return',
                                                   'Max monthly dd', 'Max drawdown', 'Lake ratio', 'Gain to Pain',
                                                   'Sharpe ratio', 'Sortino ratio'])
        kpi['Avg. monthly return'].iloc[0] = MathCalc.calc_monthly_return(portfolio['Total asset']).mean() * 100
        kpi['Pos months pct'].iloc[0] = MathCalc.positive_pct(portfolio['Returns'])
        kpi['Avg yearly return'].iloc[0] = MathCalc.calc_yearly_return(portfolio['Total asset']).mean() * 100
        kpi['Max monthly dd'].iloc[0] = MathCalc.max_drawdown(MathCalc.calc_monthly_return(portfolio['CumReturns']))
        kpi['Max drawdown'].iloc[0] = MathCalc.max_drawdown(MathCalc.calc_return(portfolio['CumReturns']))
        kpi['Lake ratio'].iloc[0] = MathCalc.calc_lake_ratio(portfolio['CumReturns'])
        kpi['Gain to Pain'].iloc[0] = MathCalc.calc_gain_to_pain(portfolio['Returns'])
        kpi['Sharpe ratio'].iloc[0] = MathCalc.sharpe_ratio(portfolio['Returns'])
        kpi['Sortino ratio'].iloc[0] = MathCalc.sortino_ratio(portfolio['Returns'])

        return kpi

    @staticmethod
    def assemble_cum_returns(returns_buyhold, returns_sharpe_optimized_buyhold, returns_minvar_optimized_buyhold):

        """
        This function assembles cumulative returns of all portfolios.
        """
        cum_returns = pd.DataFrame()
        cum_returns['BuyHold 5 Non-corr stocks'] = returns_buyhold
        cum_returns['BuyHold Sharpe-optimized'] = returns_sharpe_optimized_buyhold
        cum_returns['BuyHold MinVar-optimized'] = returns_minvar_optimized_buyhold

        return cum_returns

    @staticmethod
    def assemble_returns(returns_buyhold, returns_sharpe_optimized_buyhold, returns_minvar_optimized_buyhold):

        """
        This function assembles returns of all portfolios.
        """
        returns = pd.DataFrame()
        returns['BuyHold 5 Non-corr stocks'] = returns_buyhold
        returns['BuyHold Sharpe-optimized'] = returns_sharpe_optimized_buyhold
        returns['BuyHold MinVar-optimized'] = returns_minvar_optimized_buyhold

        return returns

    @staticmethod
    def colrow(i):
        """
        This function calculate the row and columns index number based on the total number of subplots in the plot.

        Return:
             row: axis's row index number
             col: axis's column index number
        """

        # Do odd/even check to get col index number
        if i % 2 == 0:
            col = 0
        else:
            col = 1
        # Do floor division to get row index number
        row = i // 2

        return col, row


class Trading:
    """
    This class performs trading and all other functions related to trading
    """

    def __init__(self, dow_stocks_train, dow_stocks_test, dow_stocks_volume):
        self._dow_stocks_test = dow_stocks_test
        self.dow_stocks_train = dow_stocks_train
        self.daily_v = dow_stocks_volume
        self.remaining_stocks()

    def slippage_price(self, order, price, stock_quantity, day_volume):
        """
        This function performs slippage price calculation using Zipline's volume share model
        https://www.zipline.io/_modules/zipline/finance/slippage.html
        """

        volumeShare = stock_quantity / float(day_volume)
        impactPct = volumeShare ** 2 * PRICE_IMPACT

        if order > 0:
            slipped_price = price * (1 + impactPct)
        else:
            slipped_price = price * (1 - impactPct)

        return slipped_price

    def commission(self, num_share, share_value):
        """
        This function computes commission fee of every trade
        https://www.interactivebrokers.com/en/index.php?f=1590&p=stocks1
        """

        comm_fee = 0.005 * num_share
        max_comm_fee = 0.005 * share_value

        if num_share < 1.0:
            comm_fee = 1.0
        elif comm_fee > max_comm_fee:
            comm_fee = max_comm_fee

        return comm_fee

    def find_efficient_frontier(self, data, selected):

        # reorganise data pulled by setting date as index with
        # columns of tickers and their corresponding adjusted prices
        clean = data.set_index('date')
        table = clean.pivot(columns='ticker')

        # calculate daily and annual returns of the stocks
        returns_daily = table.pct_change()
        returns_annual = returns_daily.mean() * 250

        # get daily and covariance of returns of the stock
        cov_daily = returns_daily.cov()
        cov_annual = cov_daily * 250

        # empty lists to store returns, volatility and weights of imiginary portfolios
        port_returns = []
        port_volatility = []
        sharpe_ratio = []
        stock_weights = []

        # set the number of combinations for imaginary portfolios
        num_assets = len(selected)
        num_portfolios = 50000

        # set random seed for reproduction's sake
        np.random.seed(36)

        # populate the empty lists with each portfolios returns,risk and weights
        for single_portfolio in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)
            returns = np.dot(weights, returns_annual)
            volatility = np.sqrt(np.dot(weights.T, np.dot(cov_annual, weights)))
            sharpe = returns / volatility
            sharpe_ratio.append(sharpe)
            port_returns.append(returns)
            port_volatility.append(volatility)
            stock_weights.append(weights)

        # a dictionary for Returns and Risk values of each portfolio
        portfolio = {'Returns': port_returns,
                     'Volatility': port_volatility,
                     'Sharpe Ratio': sharpe_ratio}

        # extend original dictionary to accomodate each ticker and weight in the portfolio
        for counter, symbol in enumerate(selected):
            portfolio[symbol + ' Weight'] = [Weight[counter] for Weight in stock_weights]

        # make a nice dataframe of the extended dictionary
        df = pd.DataFrame(portfolio)

        # get better labels for desired arrangement of columns
        column_order = ['Returns', 'Volatility', 'Sharpe Ratio'] + [stock + ' Weight' for stock in selected]

        # reorder dataframe columns
        df = df[column_order]

        # find min Volatility & max sharpe values in the dataframe (df)
        min_volatility = df['Volatility'].min()
        max_sharpe = df['Sharpe Ratio'].max()
        sharpe_portfolio = df.loc[df['Sharpe Ratio'] == max_sharpe]
        min_variance_portfolio = df.loc[df['Volatility'] == min_volatility]

        UserDisplay().plot_efficient_frontier(df, sharpe_portfolio, min_variance_portfolio)
        # use the min, max values to locate and create the two special portfolios
        return sharpe_portfolio, min_variance_portfolio

    def remaining_stocks(self):
        """
        This function finds out the remaining Dow component stocks after 10 randomly chosen stocks are taken.
        :return:
        """
        dow_remaining = self._dow_stocks_test.drop(RANDOM_STOCK, axis=1)
        self.dow_remaining = [i for i in dow_remaining.columns]

    def construct_book(self, dow_stocks_values, buyhold):
        """
        This function construct the trading book for stock
        """
        portfolio = pd.DataFrame(index=dow_stocks_values.index,
                                 columns=["Total asset", "ProfitLoss", "Returns", "CumReturns"])

        if buyhold:
            portfolio["Total asset"] = dow_stocks_values.sum(axis=1) + (ACCOUNT_FUND * (1 - ALLOCATION_RATIO))
        else:
            portfolio["Total asset"] = dow_stocks_values.sum(axis=1)
        portfolio["ProfitLoss"] = portfolio["Total asset"] - portfolio["Total asset"].shift(1).fillna(
            portfolio["Total asset"][0])
        portfolio["Returns"] = portfolio["Total asset"] / portfolio["Total asset"].shift(1) - 1
        portfolio["CumReturns"] = portfolio["Returns"].add(1).cumprod().fillna(1)
        return portfolio

    def diversified_trade(self, ncs, dow_stocks):
        """
        This function create trading book for the diversifed portfolios
        """
        # Calculate equally weighted fund allocation for each stock
        single_component_fund = SINGLE_TRADING_FUND / len(ncs)
        # Randomly choose the set number of stocks from DJIA pool of component stocks
        share_distribution = single_component_fund / dow_stocks.iloc[0]
        dow_stocks_values = dow_stocks.mul(share_distribution, axis=1)
        portfolio = self.construct_book(dow_stocks_values, True)
        kpi = MathCalc.calc_kpi(portfolio)
        return dow_stocks_values, portfolio, kpi

    def optimized_diversified_trade(self, ncs, sharpe_portfolio, dow_stocks):
        """
        This function create trading book for the diversifed portfolios with asset weights that are optimized by modern portfolio theory
        """

        # Calculate equally weighted fund allocation for each stock
        single_component_fund = SINGLE_TRADING_FUND * sharpe_portfolio.T.iloc[3:].values.flatten()
        # Randomly choose the set number of stocks from DJIA pool of component stocks
        share_distribution = single_component_fund / dow_stocks[ncs].iloc[0]
        dow_stocks_values = dow_stocks[non_corr_stocks].mul(share_distribution, axis=1)
        portfolio = self.construct_book(dow_stocks_values, True)
        kpi = MathCalc.calc_kpi(portfolio)
        return dow_stocks_values, portfolio, kpi

    def stocks_corr(self, portfolio_longonly_pre):
        """
        This function calculate the correlation coefficient between a portfolio returns and a stock returns
        """

        remaining_corr = pd.Series(index=self.dow_remaining)
        for stock in self.dow_remaining:
            stock_return = MathCalc.calc_return(self.dow_stocks_train[stock])
            remaining_corr[stock] = portfolio_longonly_pre['Returns'][1:].corr(stock_return)
        return remaining_corr.sort_values(ascending=True)

    def find_non_correlate_stocks(self, num_non_corr_stocks):
        """
        This function performs trade with a portfolio starting with 10 randomly chosen stocks, creating new portfolios
        each 5 more additional stock with the stocks with less correlation with the 10 stock portfolio chosen first.
        """
        add_stocks = (min(num_non_corr_stocks, len(DJI))) - 1
        # Get the returns of the long only returns of all Dow component stocks during the pre-trading period.
        single_component_fund = SINGLE_TRADING_FUND
        share_distribution = single_component_fund / self.dow_stocks_train[RANDOM_STOCK].iloc[0]
        dow_stocks_values = self.dow_stocks_train[RANDOM_STOCK].mul(share_distribution, axis=1)
        portfolio_longonly_train = self.construct_book(dow_stocks_values, True)

        # find the most uncorrelated stocks with the one randomly selected stock arranged from most
        # uncorrelated to most correlated
        remaining_corr = self.stocks_corr(portfolio_longonly_train)

        # Assemble the non-correlate stocks
        ncs = RANDOM_STOCK

        adding_stocks = [i for i in remaining_corr[0:add_stocks].index]

        # add stocks to the random portfolio stock
        ncs = ncs + adding_stocks

        # Do buy and hold trade with a simple equally weighted portfolio of the 5 non-correlate stocks
        portfolio_values, portfolio_nc_5, kpi_nc_5 = self.diversified_trade(ncs, self.dow_stocks_train[ncs])
        return portfolio_nc_5, kpi_nc_5, ncs

    def generate_signals(self, clustered_data):
        """
        This function generates regime changing signals
        """

        signals = pd.DataFrame(index=self._dow_stocks_test.index, columns=["Signal"])
        for d in self._dow_stocks_test.index:
            if clustered_data.loc[d]['Clusters'] == 0:
                signals.loc[d]["Signal"] = 2
            elif clustered_data.loc[d]['Clusters'] == 1:
                signals.loc[d]["Signal"] = -2
            elif clustered_data.loc[d]['Clusters'] == 2:
                signals.loc[d]["Signal"] = 2
            elif clustered_data.loc[d]['Clusters'] == 3:
                signals.loc[d]["Signal"] = 1
            elif clustered_data.loc[d]['Clusters'] == 4:
                signals.loc[d]["Signal"] = -1
            elif clustered_data.loc[d]['Clusters'] == 5:
                signals.loc[d]["Signal"] = 2
            elif clustered_data.loc[d]['Clusters'] == 6:
                signals.loc[d]["Signal"] = -1
            else:
                signals.loc[d]["Signal"] = 0
        self.signals = signals

    def execute_trading(self, ncs, sharpe_portfolio, clustered_data):
        """
        This function performs long only trades for a multi-assets portfolio.
        """
        self.generate_signals(clustered_data)
        # Call up trading signla caculation
        account_value = ACCOUNT_FUND
        stocks_values = pd.DataFrame(index=self._dow_stocks_test.index,
                                     columns=["Stock Price", "Stock Quantity", "Profit & Loss", "Trade Returns",
                                              "Portfolio Value", "Account Value", "Total Value"])
        stock_quantity = [0.0] * 5
        account_profit_holder = 0
        account_equity_holder = 0
        stock_weights = sharpe_portfolio.T.iloc[3:].values.flatten()
        # Slide through the timeline
        for d in self._dow_stocks_test.index:
            # if this is the first hour and signal is buy
            if (d == self._dow_stocks_test.index[0]) and (sum(stock_quantity) == 0.0) and (
                self.signals.loc[d]['Signal'] >= 1):
                if self.signals.loc[d]['Signal'] == 1:
                    single_component_fund = SINGLE_TRADING_FUND * stock_weights
                    stock_quantity = single_component_fund / self._dow_stocks_test.loc[d][ncs]
                    portfolio_value = SINGLE_TRADING_FUND
                elif self.signals.loc[d]['Signal'] == 2:
                    single_component_fund = SINGLE_TRADING_FUND * stock_weights * 2
                    stock_quantity = single_component_fund / self._dow_stocks_test.loc[d][ncs]
                    portfolio_value = SINGLE_TRADING_FUND * 2.0
                slipped_price = []
                for j, s in enumerate(ncs):
                    slipped_price.append(self.slippage_price(self.signals.loc[d]['Signal'],
                                                             self._dow_stocks_test.loc[d][s], stock_quantity[j],
                                                             self.daily_v.loc[d][s]))
                realized_pnl = 0.0
                realized_ret = float('nan')
                buy_price = slipped_price
                commission_cost = []
                for j, s in enumerate(ncs):
                    commission_cost.append(self.commission(stock_quantity[j], portfolio_value * stock_weights[j]))
                account_value = account_value - portfolio_value - sum(commission_cost)

            # if this the first hour and no trading signal
            elif d == self._dow_stocks_test.index[0] and self.signals.loc[d]['Signal'] < 1:
                stock_quantity = [0.0] * 5
                portfolio_value = 1
                realized_pnl = 0.0
                realized_ret = float('nan')
                buy_position = 0

            # if there's existing position and trading signal is sell
            elif sum(stock_quantity) > 0 and self.signals.loc[d]['Signal'] < 0:
                slipped_price = []
                for j, s in enumerate(ncs):
                    slipped_price.append(self.slippage_price(self.signals.loc[d]['Signal'],
                                                             self._dow_stocks_test.loc[d][s], stock_quantity[j],
                                                             self.daily_v.loc[d][s]))

                realized_pnl = stock_quantity * (slipped_price - buy_price)
                realized_ret = realized_pnl / (stock_quantity * buy_price)
                commission_cost = []
                for j, s in enumerate(ncs):
                    commission_cost.append(self.commission(stock_quantity[j], (stock_quantity[j] * slipped_price[j])))

                account_value = account_value + (sum(stock_quantity * slipped_price)) - sum(commission_cost)
                stock_quantity = [0.0] * 5
                portfolio_value = 0.0

                # With position, hold and no trading signal, just update portfolio value with latest price
            elif sum(stock_quantity) > 0 and self.signals.loc[d]['Signal'] >= 0:
                portfolio_value = sum(stock_quantity * self._dow_stocks_test.loc[d][ncs])
                realized_pnl = 0.0
                realized_ret = float('nan')

            # With no position, trading signal is buy
            elif sum(stock_quantity) == 0 and self.signals.loc[d]['Signal'] >= 1:
                if self.signals.loc[d]['Signal'] == 1:

                    single_component_fund = SINGLE_TRADING_FUND * stock_weights
                    stock_quantity = single_component_fund / self._dow_stocks_test.loc[d][ncs]
                    portfolio_value = SINGLE_TRADING_FUND

                elif self.signals.loc[d]['Signal'] == 2:
                    single_component_fund = SINGLE_TRADING_FUND * stock_weights * 2
                    stock_quantity = single_component_fund / self._dow_stocks_test.loc[d][ncs]
                    portfolio_value = SINGLE_TRADING_FUND * 2.0

                slipped_price = []
                for j, s in enumerate(ncs):
                    slipped_price.append(self.slippage_price(self.signals.loc[d]['Signal'],
                                                             self._dow_stocks_test.loc[d][s], stock_quantity[j],
                                                             self.daily_v.loc[d][s]))

                buy_price = slipped_price
                realized_pnl = 0.0
                realized_ret = float('nan')

                commission_cost = []
                for j, s in enumerate(ncs):
                    commission_cost.append(self.commission(stock_quantity[j], portfolio_value * stock_weights[j]))

                account_value = account_value - (sum(slipped_price * stock_quantity)) - sum(commission_cost)

            # With no position, trading signal is not buy, do nothing
            elif stock_quantity == 0 and self.signals.loc[d]['Signal'] < 1:
                realized_pnl = 0.0
                realized_ret = float('nan')

            # Record it in the stock position value book
            stocks_values["Profit & Loss"].loc[d] = realized_pnl
            stocks_values["Trade Returns"].loc[d] = realized_ret
            stocks_values["Stock Quantity"].loc[d] = stock_quantity
            stocks_values["Portfolio Value"].loc[d] = portfolio_value
            stocks_values["Stock Price"].loc[d] = self._dow_stocks_test.loc[d][ncs]
            stocks_values["Account Value"].loc[d] = account_value
            account_equity = stocks_values["Portfolio Value"].loc[d] + stocks_values["Account Value"].loc[d]
            account_profit = stocks_values["Profit & Loss"].sum()

        stocks_values["Total Value"] = stocks_values["Portfolio Value"] + stocks_values["Account Value"]
        # Calculate trading book
        portfolio_returns = self.construct_book(stocks_values["Total Value"], False)
        # Calculate trade KPI
        kpi = MathCalc.calc_kpi(portfolio_returns, stocks_values, "NCS")
        return portfolio_returns, kpi, stocks_values, self.signals