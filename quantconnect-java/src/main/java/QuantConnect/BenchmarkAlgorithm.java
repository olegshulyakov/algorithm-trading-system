/*
 * QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
 * Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License"); 
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/

package QuantConnect;

import cli.QuantConnect.Algorithm.QCAlgorithm;
import cli.QuantConnect.Data.Slice;
import cli.QuantConnect.Resolution;
import cli.QuantConnect.SecurityType;

/**
 * This algorithm is used to benchmark the Lean engine data points per second
 * <p>
 * date     | commit   | time (s) | K points/sec | Total points | Description
 * 15.04.09 | 9924b0a  | 47.50    | 338          | ~16M         | Update all securities prices before any events
 * 15.04.13 | 9acf934  | 45.77    | 350          | ~16M         | Forex portfolio modelling
 * 15.04.23 | 6fd357b  | 44.38    | 361          | ~16M         | Adds support for dividends and splits
 * 15.04.24 | d80b173  | 43.18    | 372          | ~16M         | Pre IB launch review
 * 15.04.24 | 8b4fc17  | 43.43    | 369          | ~16M         | AlgorithmManager clean up
 * 15.04.30 | 9918628  | 43.11    | 372          | ~16M         | Improve ObjectActivator performance
 * 15.04.30 | 49b398f  | 43.02    | 373          | ~16M         | DataStream sync at end of bar
 */
public class BenchmarkAlgorithm extends QCAlgorithm {
    /**
     * Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.
     */
    @Override
    public void Initialize() {
        SetStartDate(2013, 9, 15);  //Set Start Date
        SetEndDate(2013, 10, 11);    //Set End Date
        SetCash(100000);             //Set Strategy Cash
        // Find more symbols here: http://quantconnect.com/data
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "SPY", Resolution.wrap(Resolution.Tick), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "AAPL", Resolution.wrap(Resolution.Second), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "ADBE", Resolution.wrap(Resolution.Minute), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "IBM", Resolution.wrap(Resolution.Tick), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "JNJ", Resolution.wrap(Resolution.Second), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "MSFT", Resolution.wrap(Resolution.Minute), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Forex), "EURUSD", Resolution.wrap(Resolution.Tick), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Forex), "EURGBP", Resolution.wrap(Resolution.Second), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Forex), "GBPUSD", Resolution.wrap(Resolution.Minute), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Forex), "USDJPY", Resolution.wrap(Resolution.Tick), true, false);
        AddSecurity(SecurityType.wrap(SecurityType.Forex), "NZDUSD", Resolution.wrap(Resolution.Second), true, false);
    }

    /**
     * OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
     */
    @Override
    public void OnData(Slice data) {
        if (!get_Portfolio().get_Invested()) {
            SetHoldings(Symbol("SPY"), .75, false); // leave some room lest we experience a margin call!
            Debug("Purchased Stock");
        }
    }
}