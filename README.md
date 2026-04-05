# IIT-PokerBots-2026

## Aravind Ramana and Aarya Gosar  | Team Travelling_Salesmen
### Rank 5-Prelims and Finals

## Project Overview

This project implements a competitive poker bot for the IIT PokerBots 2026 competition. Our bot, developed by Team Travelling_Salesmen, achieved 5th place in the tournament. The bot uses  hand evaluation, Monte Carlo simulation, and adaptive strategies to make optimal decisions across different poker phases. Our presentation ppt explains the strategies in detailed.

## Strategy 

### Core Components

1. **Hand Strength Evaluation**
   - **Preflop**: Uses a heuristic-based strength calculation considering pair status, suitedness, and card gaps
   - **Postflop**: Employs Monte Carlo simulation with the eval7 library to estimate hand equity against opponent ranges

2. **Adaptive Bidding Strategy**
   - Auction phase bidding based on estimated hand strength
   - Dynamic bid factor adjustment based on bidding success/failure history
   - Conservative bidding for weak hands, aggressive for strong hands

3. **Betting and Calling Decisions**
   - Pot odds calculation for call/fold decisions
   - Risk-adjusted strength thresholds based on bet sizes
   - Street-specific raise amounts and frequencies
   - Special handling for revealed opponent cards

4. **Opponent Modeling**
   - Tracks opponent behavior in big bet situations
   - Adjusts strategy based on observed weak/strong play patterns
   - Incorporates revealed cards into simulation when available

### Key Features

- **Monte Carlo Simulation**: Uses 750-1125 iterations (time-adjusted) for accurate equity estimation
- **Time Management**: Dynamically adjusts simulation iterations based on remaining time bank
- **Risk Assessment**: Implements risk factors for large bets and adjusts effective strength accordingly
- **Auction Optimization**: Learns from bidding outcomes to improve auction performance
- **Multi-Street Strategy**: Different approaches for preflop, flop, turn, river, and auction phases

## Technical Implementation

### Dependencies
- `eval7`: For poker hand evaluation
- `pkbot`: Competition framework for bot execution
- Standard Python libraries: `random`, `math`

### Code Structure
- `Player` class inherits from `BaseBot`
- Main decision logic in `get_move()` method
- Hand strength calculation via `get_preflop_strength()` and `simulate()` methods
- Learning and adaptation through `on_hand_end()` callbacks

## Running the Bot

To run the bot:

```bash
python Final_submission.py [args]
```

The bot integrates with the pkbot framework and can be executed using the provided runner.




