# Capital Bikeshare: when does demand concentrate?

**Question.** If an operations team can review only a few time windows, which hours should it inspect for capacity on working and nonworking days?

**Method.** I downloaded the 2011–2012 hourly Capital Bikeshare data from the [UCI Bike Sharing dataset](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) (CC BY 4.0). A Python pipeline validates identifiers, hour ranges, unique date/hour keys, and the total-versus-component count identity, then loads a constrained SQLite table. SQL calculates average rentals per observed hour and ranks hours separately by working-day status. The [code and reproducibility steps](README.md) accompany the chart.

![Average rentals by hour and day type](outputs/hourly_profiles.svg)

**Finding.** Across 17,379 observed hourly records, working-day demand peaked at 17:00 (mean 525.29 rentals over 499 observed hours), followed by 18:00 and 08:00. Nonworking-day demand peaked at 13:00 (mean 372.73 over 231 observed hours), followed by 12:00 and 14:00. The data contain 165 absent date/hour combinations; no zero values were invented for them.

**Decision and limitations.** These windows are sensible candidates for an operations review. The dataset has no station locations, available bikes, lost demand, or costs, so it cannot prescribe rebalancing quantities or demonstrate a benefit. The data are from 2011–2012 and the means combine seasons and weather; current operations would require current station-level evidence.
