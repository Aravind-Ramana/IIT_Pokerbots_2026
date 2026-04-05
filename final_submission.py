import random
import eval7
import math
from pkbot.actions import ActionFold, ActionCall, ActionCheck, ActionRaise, ActionBid
from pkbot.states import GameInfo, PokerState
from pkbot.base import BaseBot
from pkbot.runner import parse_args, run_bot

_RANKS = '23456789TJQKA'
_SUITS = 'shdc'
_FULL_DECK_STRS = [r + s for r in _RANKS for s in _SUITS]

class Player(BaseBot):

    def __init__(self) -> None:
        self.big_bet_showdowns = 0
        self.big_bet_weak = 0
        self.bid_factor = 1.0
        self.bid_won = 0
        self.bid_lost = 0

        self.epsilon = 0.05 
        
        self.strategies = {
            'original': self._strategy1,
        }
        self.strategy_names = list(self.strategies.keys())

        self.q_values = {name: 0.0 for name in self.strategy_names}
        self.counts = {name: 0 for name in self.strategy_names}

        self.current_strategy = None
        self.last_bankroll = 0.0

    def get_preflop_strength(self, hole):
        rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }

        r1 = rank_map[hole[0][0]]
        r2 = rank_map[hole[1][0]]
        s1 = hole[0][1]
        s2 = hole[1][1]

        if r1 < r2:
            r1, r2 = r2, r1

        is_suited = (s1 == s2)
        is_pair = (r1 == r2)
        gap = r1 - r2

        if is_pair:
            equity = 0.49 + (r1 - 2) * 0.03
        else:
            equity = 0.30 + (r1 - 2) * 0.015 + (r2 - 2) * 0.015
            if is_suited:
                equity += 0.04
            if gap <= 3:
                equity += (4 - gap) * 0.01

        return max(0.0, min(0.85, equity))

    def simulate(self, hole, iterations, board, opp=None):
        if not opp:
            opp = []
        elif isinstance(opp, str):
            opp = [opp]

        hole_cards = [eval7.Card(c) for c in hole]
        board_cards = [eval7.Card(c) for c in board]
        opp_cards = [eval7.Card(c) for c in opp if c]

        known_strs = set(hole + board + opp)
        deck = [eval7.Card(c) for c in _FULL_DECK_STRS if c not in known_strs]

        need_opp = max(0, 2 - len(opp_cards))
        need_board = max(0, 5 - len(board_cards))
        total_draws = need_opp + need_board

        wins = 0
        ties = 0

        for _ in range(iterations):
            draws = random.sample(deck, total_draws)
            sim_opp_hole = opp_cards + draws[:need_opp]
            sim_board = board_cards + draws[need_opp:]

            my_val = eval7.evaluate(hole_cards + sim_board)
            opp_val = eval7.evaluate(sim_opp_hole + sim_board)

            if my_val > opp_val:
                wins += 1
            elif my_val == opp_val:
                ties += 1

        return (wins + 0.5 * ties) / max(1, iterations)

    def on_hand_start(self, game_info: GameInfo, current_state: PokerState) -> None:

        self.last_bankroll = game_info.bankroll 

        if random.random() < self.epsilon:
            self.current_strategy = random.choice(self.strategy_names)
        else:
            max_q = max(self.q_values.values())
            best_strats = [s for s, q in self.q_values.items() if q == max_q]
            self.current_strategy = random.choice(best_strats)

    def on_hand_end(self, game_info: GameInfo, current_state: PokerState) -> None:
        try:
            if current_state.opp_revealed_cards:
                opp_cards = current_state.opp_revealed_cards
                board = current_state.board
                opp_strength = self.simulate(opp_cards, 100, board, [])

                if current_state.opp_wager > 0.6 * max(1, current_state.pot):
                    self.big_bet_showdowns += 1
                    if opp_strength < 0.5:
                        self.big_bet_weak += 1
        except Exception:
            pass

        if self.current_strategy is not None:
            pnl = game_info.bankroll - self.last_bankroll
            
            self.counts[self.current_strategy] += 1
            n = self.counts[self.current_strategy]
            
            old_q = self.q_values[self.current_strategy]
            self.q_values[self.current_strategy] = old_q + (pnl - old_q) / n

    def get_move(self, game_info: GameInfo, current_state: PokerState):
        if self.current_strategy is None:
            self.current_strategy = self.strategy_names[0]

        strategy_func = self.strategies[self.current_strategy]
        return strategy_func(game_info, current_state)


    def _strategy1(self, game_info: GameInfo, current_state: PokerState):
        my_cards = current_state.my_hand
        board_cards = current_state.board
        opp_revealed = current_state.opp_revealed_cards

        if opp_revealed and isinstance(opp_revealed, str):
            opp_revealed = [opp_revealed]
        elif not opp_revealed:
            opp_revealed = []

        continue_cost = current_state.cost_to_call
        my_stack = current_state.my_chips
        pot_total = current_state.pot
        min_raise, max_raise = current_state.raise_bounds
        we_have_opp_card = len(opp_revealed) > 0

        hole_objs = [eval7.Card(c) for c in my_cards]
        board_objs = [eval7.Card(c) for c in board_cards]

        if len(hole_objs + board_objs) >= 5:
            val = eval7.evaluate(hole_objs + board_objs)
            hand_type_int = val >> 24
            
            if pot_total > 1000 and hand_type_int < 3:
                if continue_cost >= 100:
                    return ActionFold() if current_state.can_act(ActionFold) else ActionCheck()

        if current_state.street == 'preflop':
            strength = self.get_preflop_strength(my_cards)
        else:
            base_iters = 750 if current_state.street != 'river' else 500
            time_left = game_info.time_bank
            time_multiplier = max(0.2, min(1.5, time_left / 10.0))
            iters = int(base_iters * time_multiplier)
            
            strength = self.simulate(my_cards, iters, board_cards, opp_revealed)

        if current_state.street == 'auction':
            if strength < 0.1:
                bid_amount = random.randint(15, 25)
            elif strength > 0.85:
                bid_amount = int(pot_total * strength * self.bid_factor * 3)
            elif strength > 0.65:
                bid_amount = int(pot_total * strength * self.bid_factor * 2)
            else:
                bid_amount = int(pot_total * strength * self.bid_factor * 1.5)

            return ActionBid(min(bid_amount, my_stack))

        if current_state.street == 'flop':
            if not we_have_opp_card:
                self.bid_lost += 1
            else:
                self.bid_won += 1

            if self.bid_lost >= 10 and self.bid_lost >= 5 * self.bid_won:
                self.bid_factor *= 1.05
            elif self.bid_won >= 10 and self.bid_won >= 5 * self.bid_lost:
                self.bid_factor = max(1.0, self.bid_factor * 0.95)

        if current_state.street == 'preflop':
            raise_amount = int(continue_cost + 0.4 * (pot_total + continue_cost))
        else:
            raise_amount = int(continue_cost + 0.75 * (pot_total + continue_cost))

        raise_amount = max(min_raise, min(max_raise, raise_amount))

        if continue_cost > 0:
            risk_factor = 0
            if continue_cost >= 100:
                risk_factor = 0.5
            elif continue_cost > 50:
                risk_factor = 0.35
            elif continue_cost > 15:
                risk_factor = 0.20
            elif continue_cost > 6:
                risk_factor = 0.10

            if we_have_opp_card:
                risk_factor *= 0.5

            effective_strength = max(0.05, strength - risk_factor)
            pot_odds = continue_cost / (pot_total + continue_cost)

            if we_have_opp_card and current_state.street == 'river' and effective_strength > 0.2:
                if current_state.can_act(ActionCall):
                    return ActionCall()

            if effective_strength >= pot_odds:
                if current_state.street == 'preflop' and current_state.can_act(ActionRaise) and max_raise >= min_raise:
                    return ActionRaise(raise_amount)

                if effective_strength > 0.35 and current_state.can_act(ActionRaise) and max_raise >= min_raise and raise_amount <= my_stack:
                    return ActionRaise(max(min_raise, min(max_raise, 105)))

                if current_state.can_act(ActionCall):
                    return ActionCall()

            if effective_strength >= pot_odds:
                if current_state.can_act(ActionRaise) and max_raise >= min_raise and raise_amount <= my_stack:
                    if effective_strength > 0.70:
                        return ActionRaise(max(min_raise, min(max_raise, 120)))
                    elif effective_strength > 0.50:
                        return ActionRaise(raise_amount)

            return ActionFold() if current_state.can_act(ActionFold) else ActionCheck()

        else:
            if pot_total < 102 and current_state.can_act(ActionRaise) and max_raise >= min_raise:
                bet_100 = max(min_raise, min(max_raise, 102))
                if bet_100 <= my_stack:
                    return ActionRaise(bet_100)

            if not we_have_opp_card and random.random() < 0.05:
                if current_state.can_act(ActionRaise) and max_raise >= min_raise and raise_amount <= my_stack:
                    return ActionRaise(raise_amount)

            if we_have_opp_card and random.random() < 0.25:
                if current_state.can_act(ActionRaise) and max_raise >= min_raise and raise_amount <= my_stack:
                    return ActionRaise(raise_amount)

            if strength > 0.6 and current_state.can_act(ActionRaise) and max_raise >= min_raise and raise_amount <= my_stack:
                return ActionRaise(raise_amount)

            return ActionCheck()

if __name__ == '__main__':
    run_bot(Player(), parse_args())