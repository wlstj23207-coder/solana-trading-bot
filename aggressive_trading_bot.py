"""
Solana Trading Bot (Enhanced Strategy)
공격적인 롱/숏 매매 + 다중 코인
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AggressiveTrader:
    """공격적인 트레이딩 전략"""
    
    def __init__(self, initial_capital: float = 1000.0, risk_reward_ratio: float = 2.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_reward_ratio = risk_reward_ratio
        self.stop_loss_pct = 0.015  # 1.5% 스탑로스 (느슨하게)
        self.take_profit_pct = self.stop_loss_pct * risk_reward_ratio  # 3% 타겟
        
        # 포지션 관리
        self.positions = {}  # {symbol: position_info}
        
        # 거래 내역
        self.trades = []
        
        # 가격 이력 저장
        self.price_history = {}
        
        # 주요 Solana 코인 리스트
        self.solana_tokens = [
            {
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111111112',
                'name': 'Solana'
            },
            {
                'symbol': 'BONK',
                'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB',
                'name': 'Bonk'
            },
            {
                'symbol': 'WIF',
                'address': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zM',
                'name': 'dogwifhat'
            },
            {
                'symbol': 'JUP',
                'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSybKXZNsvL',
                'name': 'Jupiter'
            },
            {
                'symbol': 'RAY',
                'address': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX',
                'name': 'Raydium'
            }
        ]
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50.0  # 중립값
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        # 평균 이익/손실
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_sma(self, prices: List[float], period: int = 7) -> float:
        """이동평균 계산"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        return sum(prices[-period:]) / period
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> tuple:
        """볼린저 밴드 계산"""
        if len(prices) < period:
            return (0, 0, 0)  # 기본값
        
        sma = sum(prices[-period:]) / period
        squared_diffs = [(p - sma) ** 2 for p in prices[-period:]]
        std_dev = (sum(squared_diffs) / period) ** 0.5
        
        upper_band = sma + (2 * std_dev)
        lower_band = sma - (2 * std_dev)
        
        return (upper_band, sma, lower_band)
    
    def generate_signals(self, price_history: List[Dict], symbol: str) -> Dict:
        """매매 신호 생성 (공격적 전략)"""
        if len(price_history) < 15:  # 15 캔들부터 시작
            return {'action': 'HOLD', 'reason': 'Insufficient data'}
        
        prices = [p['price'] for p in price_history]
        current_price = prices[-1]
        
        # 지표 계산
        rsi = self.calculate_rsi(prices, 14)
        sma_7 = self.calculate_sma(prices, 7)
        sma_14 = self.calculate_sma(prices, 14)
        sma_21 = self.calculate_sma(prices, 21)
        upper_band, sma_20, lower_band = self.calculate_bollinger_bands(prices, 20)
        
        # 롱 매수 조건 (느슨하게)
        long_conditions = [
            rsi < 40,  # 과매도 완화 (30 → 40)
            sma_7 > sma_14,  # 상승추세
            current_price < lower_band,  # 볼린저 하단 밴드 터치
        ]
        
        # 숏 매도 조건 (느슨하게)
        short_conditions = [
            rsi > 60,  # 과매수 완화 (70 → 60)
            sma_7 < sma_14,  # 하락추세
            current_price > upper_band,  # 볼린저 상단 밴드 터치
        ]
        
        # 최소 조건 2개 만족하면 실행
        if sum(long_conditions) >= 2:
            return {'action': 'LONG', 'rsi': rsi, 'reason': f'RSI={rsi:.1f}, Below BB'}
        elif sum(short_conditions) >= 2:
            return {'action': 'SHORT', 'rsi': rsi, 'reason': f'RSI={rsi:.1f}, Above BB'}
        else:
            return {'action': 'HOLD', 'rsi': rsi, 'reason': 'No clear signal'}
    
    def execute_trade(self, symbol: str, action: str, price: float, timestamp: datetime):
        """거래 실행"""
        max_positions = 3  # 최대 3개 포지션 동시 보유
        
        if len(self.positions) >= max_positions:
            logger.info(f"⚠️ Max positions reached ({max_positions}), skipping {symbol}")
            return
        
        if action == 'LONG':
            # 롱 진입
            risk_amount = self.capital * 0.02  # 2% 리스크
            position_size = risk_amount / self.stop_loss_pct
            
            if self.capital >= position_size:
                self.positions[symbol] = {
                    'position': 'LONG',
                    'entry_price': price,
                    'entry_time': timestamp,
                    'size': position_size,
                    'stop_loss': price * (1 - self.stop_loss_pct),
                    'take_profit': price * (1 + self.take_profit_pct)
                }
                self.capital -= position_size  # 자금 사용
                
                logger.info(f"📈 LONG {symbol} @ ${price:.4f} | Size: ${position_size:.2f} | SL: ${price*(1-self.stop_loss_pct):.4f} | TP: ${price*(1+self.take_profit_pct):.4f}")
        
        elif action == 'SHORT':
            # 숏 진입
            risk_amount = self.capital * 0.02  # 2% 리스크
            position_size = risk_amount / self.stop_loss_pct
            
            if self.capital >= position_size:
                self.positions[symbol] = {
                    'position': 'SHORT',
                    'entry_price': price,
                    'entry_time': timestamp,
                    'size': position_size,
                    'stop_loss': price * (1 + self.stop_loss_pct),
                    'take_profit': price * (1 - self.take_profit_pct)
                }
                self.capital -= position_size  # 자금 사용
                
                logger.info(f"📉 SHORT {symbol} @ ${price:.4f} | Size: ${position_size:.2f} | SL: ${price*(1+self.stop_loss_pct):.4f} | TP: ${price*(1-self.take_profit_pct):.4f}")
    
    def check_exits(self, current_prices: Dict[str, float]):
        """청산 조건 체크"""
        for symbol, position in list(self.positions.items()):
            current_price = current_prices.get(symbol)
            
            if current_price is None:
                continue
            
            if position['position'] == 'LONG':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # 스탑로스 체크
                if pnl_pct <= -self.stop_loss_pct:
                    self.close_position(symbol, current_price, "STOP_LOSS")
                
                # 타겟 체크
                elif pnl_pct >= self.take_profit_pct:
                    self.close_position(symbol, current_price, "TAKE_PROFIT")
            
            elif position['position'] == 'SHORT':
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                # 스탑로스 체크
                if pnl_pct <= -self.stop_loss_pct:
                    self.close_position(symbol, current_price, "STOP_LOSS")
                
                # 타겟 체크
                elif pnl_pct >= self.take_profit_pct:
                    self.close_position(symbol, current_price, "TAKE_PROFIT")
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "MANUAL"):
        """포지션 청산"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        if position['position'] == 'LONG':
            pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
            pnl_amount = position['size'] * pnl_pct
        else:  # SHORT
            pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
            pnl_amount = position['size'] * pnl_pct
        
        # 자금 복귀
        self.capital += position['size'] + pnl_amount
        
        trade = {
            'symbol': symbol,
            'position': position['position'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now(),
            'reason': reason
        }
        
        self.trades.append(trade)
        
        logger.info(f"💰 CLOSE {position['position']} {symbol} @ ${exit_price:.4f} | PnL: {pnl_pct*100:+.2f}% (${pnl_amount:+.2f}) | {reason}")
        
        # 포지션 리셋
        del self.positions[symbol]
    
    def get_current_positions(self) -> Dict:
        """현재 포지션 반환"""
        return self.positions.copy()
    
    def get_capital(self) -> float:
        """현재 자금 반환"""
        return self.capital
    
    def get_trades(self) -> List:
        """거래 내역 반환"""
        return self.trades.copy()


def generate_mock_data_aggressive() -> Dict[str, List[Dict]]:
    """공격적인 모의 데이터 생성 (높은 변동성)"""
    data = {}
    
    # 각 코인별 기본 가격
    base_prices = {
        'SOL': 89.0,
        'BONK': 0.000015,
        'WIF': 2.50,
        'JUP': 1.20,
        'RAY': 2.30
    }
    
    # 30일 데이터 생성
    start_time = datetime.now()
    
    for symbol, base_price in base_prices.items():
        token_data = []
        current_price = base_price
        
        for i in range(30 * 24):  # 24개 캔들/일
            # 랜덤 가격 변동 (더 높은 변동성)
            if symbol == 'SOL':
                change_pct = random.uniform(-0.08, 0.08)  # ±8%
            elif symbol == 'BONK':
                change_pct = random.uniform(-0.15, 0.15)  # ±15%
            elif symbol == 'WIF':
                change_pct = random.uniform(-0.20, 0.20)  # ±20%
            else:
                change_pct = random.uniform(-0.12, 0.12)  # ±12%
            
            current_price *= (1 + change_pct)
            
            # 추세 추가
            if random.random() > 0.45:
                trend = random.uniform(0.0002, 0.0010)  # 상승추세 강화
            else:
                trend = random.uniform(-0.0010, -0.0002)  # 하락추세
            
            current_price *= (1 + trend)
            
            token_data.append({
                'symbol': symbol,
                'price': current_price,
                'timestamp': start_time + timedelta(hours=i)
            })
        
        data[symbol] = token_data
    
    return data


def main():
    """메인 실행 - 공격적인 다중 코인 트레이딩"""
    logger.info("=== Aggressive Multi-Coin Trading Bot ===")
    logger.info("Generating aggressive mock price data for 5 coins...")
    
    # 모의 데이터 생성
    all_data = generate_mock_data_aggressive()
    
    # 트레이더 초기화
    trader = AggressiveTrader(initial_capital=1000.0, risk_reward_ratio=2.0)
    
    logger.info(f"Initial Capital: ${trader.get_capital():.2f}")
    logger.info(f"Strategy: RSI < 40 LONG / RSI > 60 SHORT")
    logger.info(f"Stop Loss: 1.5% | Take Profit: 3% (Risk/Reward: 2x)")
    logger.info(f"Max Positions: 3")
    logger.info("")
    
    # 시뮬레이션 실행 (720 캔들 = 30일)
    signal_log = []
    
    for i in range(15, 720):  # 15 캔들부터 (데이터 누적)
        
        # 현재 가격 수집
        current_prices = {symbol: data[i]['price'] for symbol, data in all_data.items()}
        
        # 각 코인별 신호 생성 및 매매
        for symbol in ['SOL', 'BONK', 'WIF', 'JUP', 'RAY']:
            price_history = all_data[symbol][:i+1]
            signal = trader.generate_signals(price_history, symbol)
            
            current_price = current_prices[symbol]
            current_time = datetime.now()
            
            # 신호 로깅
            if signal['action'] in ['LONG', 'SHORT']:
                signal_log.append({
                    'time': i,
                    'symbol': symbol,
                    'action': signal['action'],
                    'reason': signal['reason'],
                    'price': current_price
                })
            
            # 신호에 따라 매매
            if signal['action'] == 'LONG' and symbol not in trader.positions:
                trader.execute_trade(symbol, 'LONG', current_price, current_time)
            
            elif signal['action'] == 'SHORT' and symbol not in trader.positions:
                trader.execute_trade(symbol, 'SHORT', current_price, current_time)
        
        # 청산 체크
        if i % 3 == 0:  # 3캔들마다 체크
            trader.check_exits(current_prices)
    
    # 마지막 청산
    logger.info("\nClosing all remaining positions...")
    current_prices = {symbol: data[-1]['price'] for symbol, data in all_data.items()}
    for symbol in list(trader.positions.keys()):
        trader.close_position(symbol, current_prices[symbol], "SIMULATION_END")
    
    # 결과 출력
    results = {
        'initial_capital': trader.initial_capital,
        'final_capital': trader.get_capital(),
        'total_trades': len(trader.trades),
        'trades': trader.trades
    }
    
    # 승률 계산
    winning_trades = len([t for t in trader.trades if t['pnl_pct'] > 0])
    losing_trades = len([t for t in trader.trades if t['pnl_pct'] < 0])
    win_rate = (winning_trades / results['total_trades'] * 100) if results['total_trades'] > 0 else 0
    
    total_pnl = sum(t['pnl_amount'] for t in trader.trades)
    total_return = ((results['final_capital'] - results['initial_capital']) / results['initial_capital']) * 100
    
    # 최대 손실/이익
    max_loss = min([t['pnl_amount'] for t in trader.trades]) if trader.trades else 0
    max_profit = max([t['pnl_amount'] for t in trader.trades]) if trader.trades else 0
    
    # 손익비 계산
    winning_pnls = [abs(t['pnl_pct']) for t in trader.trades if t['pnl_pct'] > 0]
    losing_pnls = [abs(t['pnl_pct']) for t in trader.trades if t['pnl_pct'] < 0]
    
    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
    actual_risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 스탑로스/타겟 횟수
    stop_losses = len([t for t in trader.trades if t['reason'] == "STOP_LOSS"])
    take_profits = len([t for t in trader.trades if t['reason'] == "TAKE_PROFIT"])
    
    # 코인별 거래
    symbol_trades = {}
    for trade in trader.trades:
        symbol = trade['symbol']
        if symbol not in symbol_trades:
            symbol_trades[symbol] = []
        symbol_trades[symbol].append(trade)
    
    logger.info("\n" + "="*70)
    logger.info("📊 FINAL RESULTS - AGGRESSIVE MULTI-COIN TRADING")
    logger.info("="*70)
    logger.info(f"Initial Capital:  ${results['initial_capital']:.2f}")
    logger.info(f"Final Capital:    ${results['final_capital']:.2f}")
    logger.info(f"Total Return:     {total_return:+.2f}%")
    logger.info(f"Total PnL:       ${total_pnl:+.2f}")
    logger.info("")
    logger.info(f"Total Trades:     {results['total_trades']}")
    logger.info(f"Winning Trades:   {winning_trades} ({win_rate:.1f}%)")
    logger.info(f"Losing Trades:   {losing_trades}")
    logger.info("")
    logger.info(f"Avg Win:         {avg_win*100:.2f}%")
    logger.info(f"Avg Loss:        {avg_loss*100:.2f}%")
    logger.info(f"Actual Risk/Reward: {actual_risk_reward:.2f}x")
    logger.info(f"Target Risk/Reward: {trader.risk_reward_ratio:.2f}x")
    logger.info("")
    logger.info(f"Stop Losses:     {stop_losses}")
    logger.info(f"Take Profits:    {take_profits}")
    logger.info("")
    logger.info(f"Max Profit:       ${max_profit:+.2f}")
    logger.info(f"Max Loss:        ${max_loss:+.2f}")
    
    # 코인별 결과
    logger.info("")
    logger.info("Coin-by-Coin Results:")
    for symbol, trades in symbol_trades.items():
        if trades:
            coin_pnl = sum(t['pnl_amount'] for t in trades)
            coin_trades_count = len(trades)
            coin_wins = len([t for t in trades if t['pnl_pct'] > 0])
            coin_win_rate = (coin_wins / coin_trades_count * 100) if coin_trades_count > 0 else 0
            
            logger.info(f"  {symbol}: {coin_trades_count} trades | {coin_win_rate:.1f}% win rate | ${coin_pnl:+.2f} PnL")
    
    logger.info("="*70)
    
    # 신호 통계
    logger.info("\nSignal Statistics:")
    logger.info(f"Total Signals: {len(signal_log)}")
    long_signals = len([s for s in signal_log if s['action'] == 'LONG'])
    short_signals = len([s for s in signal_log if s['action'] == 'SHORT'])
    logger.info(f"LONG Signals: {long_signals}")
    logger.info(f"SHORT Signals: {short_signals}")
    
    # 결과 저장
    final_results = {
        'summary': {
            'initial_capital': results['initial_capital'],
            'final_capital': results['final_capital'],
            'total_return': total_return,
            'total_pnl': total_pnl,
            'total_trades': results['total_trades'],
            'win_rate': win_rate,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'actual_risk_reward': actual_risk_reward
        },
        'by_symbol': {
            symbol: {
                'trades': len(trades),
                'pnl': sum(t['pnl_amount'] for t in trades),
                'win_rate': coin_win_rate if trades else 0
            }
            for symbol, trades in symbol_trades.items()
        },
        'signals': signal_log,
        'trades': results['trades']
    }
    
    with open('aggressive_trading_results.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to aggressive_trading_results.json")


if __name__ == "__main__":
    main()
