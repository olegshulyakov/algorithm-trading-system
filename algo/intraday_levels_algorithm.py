"""
This algorithm trades on price levels 0.00, 0.25, 0.50, 0.75.
"""
import logbook
import numpy as np

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
intraday_trend_fast = 10  # in minutes
intraday_trend_slow = 30  # in minutes
intraday_cents_to_level = 2

log = logbook.Logger("ZiplineLog")

def initialize(context):
    """
    Called once at the start of the algorithm.
    """
    # Skiping leverage
    set_max_leverage(0.0)

    # Rebalance every day, 1 hour after market open.
    schedule_function(
        my_rebalance,
        date_rules.every_day(),
        time_rules.every_minute()
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
    average_true_range = SimpleMovingAverage(inputs=[USEquityPricing.high], window_length=10) - SimpleMovingAverage(
        inputs=[USEquityPricing.low], window_length=10)

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
    record(leverage=context.account.leverage, long_count=longs, short_count=shorts)


def handle_data(context, data):
    """
    Called every minute.
    """

    # Getting stock with up-trend
    up_trend = up_trend_intraday(context.long_secs, data)
    # Getting stock with long box
    box_to_buy = long_box(context.long_secs, data)
    # Combine rules
    should_buy = np.equal(up_trend, box_to_buy)

    # for stock in context.short_secs:
    #    if (data.can_trade(stock)):
    #        order_target_value(stock, -shares_amount, style=LimitOrder(limit_price, exchange=IBExchange.SMART))


def up_trend_intraday(securities, data):
    """
    Calculates down-trend intraday
    """
    sma_fast = data.history(securities, "low", bar_count=intraday_trend_fast, frequency=intraday_frequency).mean()

    sma_slow = data.history(securities, "low", bar_count=intraday_trend_slow, frequency=intraday_frequency).mean()

    trend = np.greater(sma_fast, sma_slow)

    log.debug("Up-trend stocks: " + ", ".join([security_.symbol for security_ in securities[trend == True]]))

    return trend


def down_trend_intraday(securities, data):
    """
    Calculates down-trend intraday
    """

    sma_fast = data.history(securities, "high", bar_count=intraday_trend_fast, frequency=intraday_frequency).mean()

    sma_slow = data.history(securities, "high", bar_count=intraday_trend_slow, frequency=intraday_frequency).mean()

    trend = np.less(sma_fast, sma_slow)

    log.debug("Down-trend stocks: " + ", ".join([security_.symbol for security_ in securities[trend == True]]))

    return trend


def long_box(securities, data):
    """
    Shows that stock has buy box on level
    """

    prices = data.history(securities, "low", bar_count=intraday_trend_fast, frequency=intraday_frequency)
    # Get minimum price
    min_price = prices.min()
    # Check that all prices are near each other
    if (np.greater(np.add(prices, -min_price).max()),
        intraday_cents_to_level):  # bug in np.add(prices, -min_price) - wrong dimentions
        return np.zeros(prices.shape, dtype=bool)

    # Count distance to .25 level
    cents_to_level = np.mod(np.multiply(min_price, 100), 25)
    box = np.less_equal(cents_to_level, intraday_cents_to_level)  # maximux intraday_cents_to_level cents from level

    return box


def short_box(securities, data):
    """
    Shows that stock has sell box on level
    """

    return False


class TrendFactor(CustomFactor):
    """
    Computes the trend strenght.

    Pre-declares high and low as default inputs and `window_length` as 1.
    """

    inputs = [USEquityPricing.high, USEquityPricing.low]
    outputs = ['long', 'short']
    window_length = 15

    def compute(self, today, assets, out, high, low):
        # Initialization
        out.long = np.nan_to_num(out.long)
        out.short = np.nan_to_num(out.short)

        i = self.window_length - 1
        # Calculate trends recursively
        while (i > 0):
            # Calculate long trend size
            up_trend = np.greater_equal(low[-i], low[-i - 1])
            # log.debug(str(up_trend))
            # log.debug(str(out.long))
            out.long[up_trend == True] += 1
            # log.debug(str(out.long))
            out.long[up_trend == False] = 0
            # log.debug(str(out.long))

            # Calculate short trend size
            down_trend = np.less_equal(high[-i], high[-i - 1])
            out.short[down_trend == True] += 1
            out.short[down_trend == False] = 0
            i = i - 1
