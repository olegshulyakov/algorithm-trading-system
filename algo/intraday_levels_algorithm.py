"""
This algorithm trades on price levels 0.00, 0.25, 0.50, 0.75.
"""
import logbook
import numpy

from zipline.api import (
    attach_pipeline,
    date_rules,
    order,
    pipeline_output,
    record,
    schedule_function,
    set_max_leverage,
    time_rules,
)
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
intraday_trend_fast = 10 # in minutes
intraday_trend_slow = 30 # in minutes
intraday_cents_to_level = 2

log = logbook.Logger("ZiplineLog")

def initialize(context):
    """
    Called once at the start of the algorithm.
    """
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

    # Record tracking variables at the end of each day.
    schedule_function(
        my_record_vars,
        date_rules.every_day(),
        time_rules.market_close()
    )

    # Create our dynamic stock selector.
    attach_pipeline(make_screener(), 'stock_screener')


def make_screener(self):
    """
    Daily screener for securities to trade
    """

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
    """
    Called every day before market open.
    """

    # Pipeline_output returns a pandas DataFrame with the results of our factors
    # and filters.
    context.output = pipeline_output('stock_screener')

    # Sets the list of securities we want to long as the securities with a 'True'.
    context.long_secs = context.output[context.output['long'] >= daily_trend_strength].index

    # Sets the list of securities we want to short as the securities with a 'True'.
    context.short_secs = context.output[context.output['short'] >= daily_trend_strength].index

    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index

    # A set of the same securities, sets have faster lookup.
    context.security_set = set(context.security_list)

    # log.debug('Securities: ' + str(context.output))
    log.info('Found securities to trade: ' + str(len(context.security_list)))
    log.info('Found securities to trade LONG: ' + str(len(context.long_secs)))
    log.info('Found securities to trade SHORT: ' + str(len(context.short_secs)))

    # Log the long and short orders each week.
    log.info("Today's longs: " + ", ".join([long_.symbol for long_ in context.long_secs]))
    log.info("Today's shorts: " + ", ".join([short_.symbol for short_ in context.short_secs]))


def close_positions(context, data):
    """
    This function is called before market close everyday and closes all open positions.
    """
    for position in context.portfolio.positions:
        log.debug(
            'Closing position for ' + position.sid + ', amount: ' + position.amount + ', cost: ' + position.cost_basis)

        order(position.sid, position.amount)


def my_rebalance(context, data):
    """
    Execute orders according to our schedule_function() timing.
    """
    pass


def my_record_vars(context, data):
    """
    This function is called at the end of each day and plots certain variables.
    """
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
    record(leverage = context.account.leverage, long_count=longs, short_count=shorts)


def handle_data(context, data):
    """
    Called every minute.
    """

    to_buy = filter_securities_to_buy(context.long_secs, data)
    if to_buy:
        log.debug("Up-trend stocks: "+", ".join([security_.symbol for security_ in to_buy]))


def filter_securities_to_buy(securities, data):
    """
    Filters securities that we should buy
    """
    result_list = []
    for security in securities:
        data_history_fast = data.history(security, "low", intraday_trend_fast, intraday_frequency).as_matrix()
        data_history_slow = data.history(security, "low", intraday_trend_slow, intraday_frequency).as_matrix()

        if (numpy.isnan(data_history_fast).any() or numpy.isnan(data_history_fast).any()):
            continue

        # calculating up-trend intraday
        sma_fast = data_history_fast.mean()
        sma_slow = data_history_slow.mean()

        if (sma_fast < sma_slow):
            continue

        prices = data_history_fast
        # get minimum price
        min_price = prices.min()

        # count distance to .25 level
        cents_to_level = 100 * min_price % 25

        # check that price is near level
        if (cents_to_level > intraday_cents_to_level):
            continue

        # Check that all prices are near minimum
        difference_to_minimum = numpy.subtract( prices, min_price * numpy.ones(prices.shape) ) * 100

        if (difference_to_minimum.max() > intraday_cents_to_level):
            continue

        result_list.append(security)

    return result_list


class TrendFactor(CustomFactor):
    """
    Computes the trend strenght.

    Pre-declares high and low as default inputs and `window_length` as 1.
    """

    inputs = [USEquityPricing.high,USEquityPricing.low]
    outputs = ['long', 'short']
    window_length = 15

    def compute(self, today, assets, out, high, low):
        # Initialization
        out.long = numpy.nan_to_num(out.long)
        out.short = numpy.nan_to_num(out.short)

        i = self.window_length - 1
        # Calculate trends recursively
        while (i > 0):
            # Calculate long trend size
            up_trend = numpy.greater_equal(low[-i], low[-i-1])
            #log.debug(str(up_trend))
            #log.debug(str(out.long))
            out.long[up_trend == True] += 1
            #log.debug(str(out.long))
            out.long[up_trend == False] = 0
            #log.debug(str(out.long))

            # Calculate short trend size
            down_trend = numpy.less_equal(high[-i], high[-i-1])
            out.short[down_trend == True] += 1
            out.short[down_trend == False] = 0
            i = i - 1
