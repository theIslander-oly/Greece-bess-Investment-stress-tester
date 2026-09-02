# Greek Battery Tool Explained Like I'm 12 (ELI12)

## Overview: What Does This Tool Do?

This is a **simulation tool** for analyzing whether a large-scale battery energy storage system (BESS) could be profitable in Greece's Day-Ahead Electricity Market (DAM). It takes real historical electricity prices and tests different strategies for when to buy (charge) and when to sell (discharge) electricity.

The tool is specifically designed to answer: *"If we operated a battery in Greece and traded only in the day-ahead market, how profitable could it be?"*

## The Core Concept: Energy Arbitrage

**Energy arbitrage** means buying low and selling high:

```
Morning:  Electricity price is €20/MWh → Battery CHARGES (buys electricity)
         ↓
Afternoon: Electricity price is €80/MWh → Battery DISCHARGES (sells electricity)
         ↓
Profit: (€80 - €20) × MWh = Profit!
```

But here's the catch: you need to account for **efficiency losses**. When you store electricity and get it back, you lose some as heat. A typical battery might keep 88% of the energy (losing 12%).

## Three Analytical Methods

### Method 1: Perfect Foresight (The Upper Bound)

This calculates the **theoretical maximum profit** if the battery somehow knew every future price.

**How it works:**
- Use a mathematical optimizer (like solving a complex puzzle)
- Know all prices for an entire year in advance
- Calculate the exact optimal charge/discharge schedule
- This gives you the profit ceiling

**Example:** With perfect knowledge, a 50 MW / 100 MWh battery might make €2.16 million on 2023 prices.

**Important:** This is IMPOSSIBLE in real life. It's just a reference point to compare against.

### Method 2: Forecast-Based Trading (Realistic)

This uses actual forecasting methods to guess tomorrow's prices based on historical patterns:

**Naive (Simple) Methods:**
- **Daily persistence:** "Tomorrow will be like today"
- **Weekly persistence:** "Tomorrow will be like last Wednesday"
- **Rolling mean:** "Tomorrow will be the average of the last 2 weeks"

**Machine Learning Method:**
- The computer learns patterns from 2-3 years of historical data
- Uses features like day-of-week, time-of-day, and past price trends
- Makes predictions and the battery trades based on those predictions

**Example:** Using these forecasts, the same battery might make €1.2-1.5 million (about 60-70% of the theoretical maximum).

### Method 3: Stress Testing (What-If Scenarios)

This tests how the battery performs under challenging conditions:

**Scenario Examples:**
- **Price compression:** What if prices only varied half as much? (realistic as more batteries enter the market)
- **Degradation:** What if the battery loses capacity over time?
- **Outages:** What if the battery is unavailable on certain days?
- **Bootstrap scenarios:** Create synthetic price paths that are statistically similar to historical data

## The Math Behind It

The tool uses a **mathematical optimization solver** to solve this problem:

**Constraints (Rules the battery must follow):**
- Can't charge faster than the power rating (e.g., max 50 MW)
- Can't store more than the tank size (e.g., max 100 MWh)
- Can't charge AND discharge at the same time
- Charge efficiency: 95%, Discharge efficiency: 93%

**Objective (What we're maximizing):**
- Revenue from selling electricity
- Minus the cost of buying electricity
- Minus efficiency losses
- Minus degradation costs
- Minus market fees

The solver finds the optimal trading schedule that respects all constraints.

## Key Features

### 1. Accurate Price Data
- Uses official Greek prices from HEnEx and ENTSO-E
- Validates for missing prices, duplicates, and errors
- Properly handles daylight saving time transitions (some days have 23 hours, others 25)

### 2. Battery Degradation Model
- Tracks how battery capacity decreases over time
- Models calendar aging (time-based degradation)
- Models cycle aging (charge/discharge degrades batteries)
- Accounts for potential battery replacement/upgrade scenarios

### 3. Financial Analysis
- Calculates Net Present Value (NPV)
- Calculates Internal Rate of Return (IRR)
- Includes capital costs (buying the battery)
- Includes operating costs (maintenance, staff)
- Estimates residual value (what the battery is worth at the end)

## Important Limitations

### What It DOESN'T Model

1. **Intraday trading:** Only day-ahead market, not the more frequent intraday trades that might be profitable
2. **Balancing services:** Batteries can earn money from grid balancing (they offer this now, but not modeled here)
3. **Government support:** State availability contracts (which real Greek batteries use) aren't modeled
4. **Market competition:** Battery forecasts assume other batteries won't drive prices down (but real batteries will)
5. **Taxes and subsidies:** Not included in the financial calculations
6. **Grid constraints:** Assumes the battery can freely buy/sell any amount

### Why This Matters

Real batteries in Greece earn money from multiple sources. This tool only looks at day-ahead arbitrage. So:
- Real batteries would probably make MORE money (from balancing services)
- But also LESS money (because more batteries entering the market will compress prices)

## How the Tool Works: Step-by-Step

```
1. Load official Greek electricity prices (2020-2026)
   ↓
2. Normalize prices to standard format (UTC time, quality checks)
   ↓
3. Calculate perfect-foresight optimum
   ↓
4. Create price forecasts using multiple methods
   ↓
5. Simulate trading using each forecast method
   ↓
6. Track battery degradation over time
   ↓
7. Convert operating decisions into cash flows
   ↓
8. Calculate financial metrics (NPV, IRR, payback)
   ↓
9. Run stress scenarios (price compression, outages, etc.)
   ↓
10. Generate HTML report with all results
```

## Reading the Results

A typical output looks like:

```
Perfect Foresight (upper bound):     €2,162,101
Simple Forecast (daily persistence):  €1,195,000
ML Forecast (machine learning):       €1,287,000
30% Price Compression:                  €712,000
After 10 years degradation:             €856,000
```

**What this means:**
- If you could see the future: €2.16M/year
- With realistic forecasts: €1.2-1.3M/year (55-60% capture)
- If prices get cheaper: €712K/year
- Accounting for battery aging: €856K/year

## Why Use This Tool?

**Good for:**
- Understanding the basics of battery economics
- Exploring "what-if" scenarios
- Teaching energy market concepts
- Research and feasibility studies

**NOT good for:**
- Making actual investment decisions
- Predicting future prices
- Modeling real battery projects (needs more features)

## The Caution Label (Important!)

Every output from this tool says: *"This is a historical replay/forecast backtest, not expected revenue. This is not investment advice."*

Why? Because:
1. History doesn't predict the future
2. Other batteries weren't in the market then (now they are)
3. The tool has simplified assumptions
4. Real projects need much more analysis

## Summary

**What it does:** Simulates buying and selling electricity in Greece, testing both perfect knowledge and realistic forecasts.

**Why it matters:** Shows if battery energy storage could be profitable in Greece's day-ahead market, and how sensitive profits are to forecast accuracy and market conditions.

**What you need to know:** Use this as a research and learning tool, not for making real investment decisions.

