"""
This algorithm trades on price levels 0.00, 0.25, 0.50, 0.75.
"""
import logbook
import numpy

from zipline.api import (
    attach_pipeline,
    date_rules,
    order_target,
    pipeline_output,
    record,
    schedule_function,
    set_max_leverage,
    time_rules,
    set_slippage,
    set_commission,
)
from zipline.finance import slippage, commission
from zipline.finance.execution import LimitOrder
from zipline.pipeline import Pipeline, CustomFactor
from zipline.pipeline.data import USEquityPricing
from zipline.pipeline.factors import SimpleMovingAverage

"""
Algorithm constants
"""
daily_trend_strength = 2
minimum_daily_volume = 1000000
minimum_atr = 0.5
shares_amount = 100
intraday_frequency = "1m"
intraday_trend_fast = 10  # in minutes
intraday_trend_slow = 30  # in minutes
intraday_cents_to_level = 2

position_amount = 500  # shares
stop_size = 0.05  # in dollars
target_profit = 0.20  # in dollars
cents_to_market = 0.02

log = logbook.Logger("ZiplineLog")

def initialize(context):
    """ Called once at the start of the algorithm. """

    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))
    set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.00))
    set_max_leverage(1.0)

    # Rebalance every day, 1 hour after market open.
    schedule_function(
        my_rebalance,
        date_rules.every_day(),
        time_rules.market_open(hours=1)
    )

    # Close all positions every day, 30 minutes before market close.
    schedule_function(
        close_positions,
        date_rules.every_day(),
        time_rules.market_close(minutes=30)
    )

    # Create our dynamic stock selector.
    attach_pipeline(make_screener(), 'stock_screener')


def make_screener():
    """ Daily screener for securities to trade """

    #  Average volume for last 2 weeks.
    average_volume = SimpleMovingAverage(inputs=[USEquityPricing.volume], window_length=10)

    # SMA for last 2 weeks.
    sma_10 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=10)

    # ATR for last 2 weeks
    average_true_range = SimpleMovingAverage(inputs=[USEquityPricing.high], window_length=10) - SimpleMovingAverage(inputs=[USEquityPricing.low], window_length=10)

    long, short = TrendFactor()

    # Takin securities with price between [5, 50], average volume over million and ATR >= 0.5
    return Pipeline(
        columns={
            'average_volume': average_volume,
            'average_true_range': average_true_range,
            'long': long,
            'short': short
        },
        screen=(
            (average_volume > minimum_daily_volume) &
            (sma_10 >= 5) &
            (sma_10 <= 50) &
            (average_true_range >= minimum_atr)
        )
    )


def before_trading_start(context, data):
    """ Called every day before market open. """

    # Pipeline_output returns a pandas DataFrame with the results of our factors
    # and filters.
    context.output = pipeline_output('stock_screener')

    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index

    # A set of the same securities, sets have faster lookup.
    context.security_set = set(context.security_list)

    # log.debug('Securities: ' + str(context.output))
    log.info('Found securities to trade: ' + str(len(context.security_list)))

    # Sets the list of securities we want to long as the securities with a 'True'.
    long_secs = context.output[context.output['long'] >= daily_trend_strength].index
    context.long_trader = LongTrader(context, data, long_secs)

    # Sets the list of securities we want to short as the securities with a 'True'.
    short_secs = context.output[context.output['short'] >= daily_trend_strength].index
    context.short_trader = LongTrader(context, data, short_secs)


def close_positions(context, data):
    """ This function is called before market close everyday and closes all open positions. """

    for position in context.portfolio.positions.itervalues():
        log.debug('Closing position for ' + str(position.sid) + ', amount: ' + str(position.amount) + ', cost: ' + str(position.cost_basis))
        order_target(position.sid, 0)

    my_record_vars(context, data)

def my_rebalance(context, data):
    """ Execute orders according to our schedule_function() timing. """
    pass


def my_record_vars(context, data):
    """ This function is called at the end of each day and plots certain variables. """
    # Check how many long and short positions we have.
    longs = shorts = 0
    for position in context.portfolio.positions.itervalues():
        if position.amount > 0:
            longs += 1
        if position.amount < 0:
            shorts += 1

    # Record and plot the leverage of our portfolio over time as well as the
    # number of long and short positions. Even in minute mode, only the end-of-day
    # leverage is plotted.
    record(leverage=context.account.leverage, long_count=longs, short_count=shorts)


def handle_data(context, data):
    """ Called every minute. """
    context.long_trader.trade()
    context.short_trader.trade()
    my_record_vars(context, data)


class LongTrader():
    """ Class to open and close long positions """

    def __init__(self, context, data, securities):
        self.context = context
        self.data = data
        self.securities = securities
        log.info('Found securities to trade : ' + str(len(securities)))
        log.info("Today's longs: " + ", ".join([security_.symbol for security_ in securities]))

    def trade(self):
        self.open()
        self.close()

    def open(self):
        """ Open long positions """

        securities_to_buy = self.filter_securities(self.securities, self.data)
        if securities_to_buy:
            log.debug("Up-trend stocks: " + ", ".join([security_.symbol for security_ in securities_to_buy]))

        for security in securities_to_buy:

            if security in self.context.portfolio.positions.keys():
                continue

            price = self.data.history(security, "low", intraday_trend_fast, intraday_frequency).as_matrix().min() + cents_to_market
            order_target(security, position_amount, style=LimitOrder(price))
            log.info("Buying " + str(security.symbol) + ", price  =" + str(price))

    def close(self):
        """ Check long positions to close """

        for position in self.context.portfolio.positions.itervalues():

            if position.amount < 0:
                continue

            stop_price = position.cost_basis - stop_size
            target_price = position.cost_basis + target_profit
            if position.last_sale_price <= stop_price or position.last_sale_price >= target_price:
                log.debug("Closing " + str(position))
                order_target(position.sid, 0)

    def filter_securities(self, securities, data):
        """ Filters securities that we should buy """
        result_list = []
        for security in securities:

            if not data.can_trade(security):
                continue

            data_history_fast = data.history(security, "low", intraday_trend_fast, intraday_frequency).as_matrix()
            data_history_slow = data.history(security, "low", intraday_trend_slow, intraday_frequency).as_matrix()

            if numpy.isnan(data_history_fast).any() or numpy.isnan(data_history_fast).any():
                continue

            # calculating up-trend intraday
            sma_fast = data_history_fast.mean()
            sma_slow = data_history_slow.mean()

            if sma_fast < sma_slow:
                continue

            prices = data_history_fast
            # get minimum price
            min_price = prices.min()

            # count distance to .25 level
            cents_to_level = 100 * min_price % 25

            # check that price is near level
            if cents_to_level > intraday_cents_to_level:
                continue

            # Check that all prices are near minimum
            difference_to_minimum = numpy.subtract(prices, min_price * numpy.ones(prices.shape)) * 100

            if difference_to_minimum.max() > intraday_cents_to_level:
                continue

            result_list.append(security)

        return result_list


class ShortTrader():
    """ Class to open and close long positions """

    def __init__(self, context, data, securities):
        self.context = context
        self.data = data
        self.securities = securities
        log.info('Found securities to trade : ' + str(len(securities)))
        log.info("Today's shorts: " + ", ".join([security_.symbol for security_ in securities]))

    def trade(self):
        self.open()
        self.close()

    def open(self):
        """ Open short positions """

        securities_to_sell = self.filter_securities(self.securities, self.data)
        if securities_to_sell:
            log.debug("Down-trend stocks: " + ", ".join([security_.symbol for security_ in securities_to_sell]))

        for security in securities_to_sell:

            if security in self.context.portfolio.positions.keys():
                continue

            price = self.data.history(security, "high", intraday_trend_fast, intraday_frequency).as_matrix().max() - cents_to_market
            order_target(security, -position_amount, style=LimitOrder(price))
            log.info("Selling " + str(security.symbol) + ", price  =" + str(price))

    def close(self):
        """ Check short positions to close """

        for position in self.context.portfolio.positions.itervalues():

            if position.amount > 0:
                continue

            stop_price = position.cost_basis + stop_size
            target_price = position.cost_basis - target_profit
            if position.last_sale_price >= stop_price or position.last_sale_price <= target_price:
                log.debug("Closing " + str(position))
                order_target(position.sid, 0)

    def filter_securities(self, securities, data):
        """ Filters securities that we should sell """
        result_list = []
        for security in securities:

            if not data.can_trade(security):
                continue

            data_history_fast = data.history(security, "high", intraday_trend_fast, intraday_frequency).as_matrix()
            data_history_slow = data.history(security, "high", intraday_trend_slow, intraday_frequency).as_matrix()

            if numpy.isnan(data_history_fast).any() or numpy.isnan(data_history_fast).any():
                continue

            # calculating up-trend intraday
            sma_fast = data_history_fast.mean()
            sma_slow = data_history_slow.mean()

            if sma_fast > sma_slow:
                continue

            prices = data_history_fast
            # get minimum price
            max_price = prices.max()

            # count distance to .25 level
            cents_to_level = 100 - 100 * max_price % 25

            # check that price is near level
            if (cents_to_level > intraday_cents_to_level):
                continue

            # Check that all prices are near minimum
            difference_to_minimum = numpy.subtract(prices, max_price * numpy.ones(prices.shape)) * 100

            if (100 - difference_to_minimum.max()) > intraday_cents_to_level:
                continue

            result_list.append(security)

        return result_list


class TrendFactor(CustomFactor):
    """ Computes the trend strenght. Pre-declares high and low as default inputs and `window_length` as 1. """

    inputs = [USEquityPricing.high, USEquityPricing.low]
    outputs = ['long', 'short']
    window_length = 15

    def compute(self, today, assets, out, high, low):
        # Initialization
        out.long = numpy.nan_to_num(out.long)
        out.short = numpy.nan_to_num(out.short)

        i = self.window_length - 1
        # Calculate trends recursively
        while i > 0:
            # Calculate long trend size
            up_trend = numpy.greater_equal(low[-i], low[-i - 1])
            # log.debug(str(up_trend))
            # log.debug(str(out.long))
            out.long[up_trend == True] += 1
            # log.debug(str(out.long))
            out.long[up_trend == False] = 0
            # log.debug(str(out.long))

            # Calculate short trend size
            down_trend = numpy.less_equal(high[-i], high[-i - 1])
            out.short[down_trend == True] += 1
            out.short[down_trend == False] = 0
            i = i - 1
