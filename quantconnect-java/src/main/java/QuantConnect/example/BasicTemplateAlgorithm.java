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
package QuantConnect.example;

import cli.QuantConnect.Algorithm.QCAlgorithm;
import cli.QuantConnect.Data.Slice;
import cli.QuantConnect.Resolution;
import cli.QuantConnect.SecurityType;

/**
 * <summary>
 * Basic template algorithm simply initializes the date range and cash
 * </summary>
 */
public class BasicTemplateAlgorithm extends QCAlgorithm {
    /**
     * <summary>
     * Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.
     * </summary>
     */
    public void Initialize() {
        SetStartDate(2013, 10, 7);  //Set Start Date
        SetEndDate(2013, 10, 11);    //Set End Date
        SetCash(100000);             //Set Strategy Cash
        // Find more symbols here: http://quantconnect.com/data
        AddSecurity(SecurityType.wrap(SecurityType.Equity), "SPY", Resolution.wrap(Resolution.Second), true, false);
    }

    /**
     * <summary>
     * OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
     * </summary>
     * <param name="data">Slice object keyed by symbol containing the stock data</param>
     */
    public void OnData(Slice data) {
        if (!get_Portfolio().get_Invested()) {
            SetHoldings(Symbol("SPY"), 1, false);
            Debug("Hello From Java");
        }
    }
}