package QuantConnect.example.Benchmarks;

import cli.QuantConnect.Algorithm.QCAlgorithm;
import cli.QuantConnect.Data.Slice;
import cli.QuantConnect.Resolution;
import cli.QuantConnect.SecurityType;

public class EmptyMinute400EquityAlgorithm extends QCAlgorithm {

    @Override
    public void Initialize() {
        SetStartDate(2015, 9, 28);
        SetEndDate(2015, 11, 13);
        for (String symbol : Symbols.Equity.All) {
            AddSecurity(SecurityType.wrap(SecurityType.Equity), symbol, Resolution.wrap(Resolution.Minute), true, false);
        }
    }

    @Override
    public void OnData(Slice slice) {
    }
}
