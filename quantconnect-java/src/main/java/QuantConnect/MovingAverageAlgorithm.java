package QuantConnect;

import cli.QuantConnect.Algorithm.QCAlgorithm;
import cli.QuantConnect.Data.Slice;
import cli.QuantConnect.Resolution;
import cli.QuantConnect.SecurityType;
import cli.System.DateTime;

/**
 * Created by user on 9/18/16.
 */
public class MovingAverageAlgorithm extends QCAlgorithm {

    @Override
    public void Initialize() {
        super.Initialize();
        SetStartDate(new DateTime(2006, 1, 1));
        SetEndDate(new DateTime(2016, 9, 15));
        SetCash(100000);

        SetBenchmark(Symbol("SPY"));
        // Find more symbols here: http://quantconnect.com/data
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "SPY", Resolution.wrap(Resolution.Minute), true, false);
    }

    @Override
    public void OnData(Slice slice) {
        super.OnData(slice);

        if (!get_Portfolio().get_Invested()) {
            SetHoldings(Symbol("SPY"), 1, false);
            Debug("Hello From Java");
        }
    }
}
