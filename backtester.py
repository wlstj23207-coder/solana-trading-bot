"""
Solana Trading Backtester
손익비 1:2 기반 자동매매 시뮬레이션
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingStrategy:
    """트레이딩 전략"""
    
    def __init__(self, risk_reward_ratio: float = 2.0):
        self.risk_reward_ratio = risk_reward_ratio
        self.stop_loss_pct = 0.02  # 2% 스탑로스
        self.take_profit_pct = self.stop_loss_pct * risk_reward_ratio  # 4% 타겟
    
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
    
    def generate_signals(self, price_history: List[Dict]) -> str:
        """매매 신호 생성"""
        if len(price_history) < 21:
            return "HOLD"  # 데이터 부족
        
        prices = [p['price'] for p in price_history]
        
        # RSI 계산
        rsi = self.calculate_rsi(prices, 14)
        
        # 이동평균 계산
        sma_7 = self.calculate_sma(prices, 7)
        sma_14 = self.calculate_sma(prices, 14)
        sma_21 = self.calculate_sma(prices, 21)
        
        current_price = prices[-1]
        
        # 매수 조건
        buy_conditions = [
            rsi < 30,  # 과매도
            sma_7 > sma_14 > sma_21,  # 상승추세
            current_price > sma_21  # 상승추세 확인
        ]
        
        # 매도 조건
        sell_conditions = [
            rsi > 70,  # 과매수
            sma_7 < sma_14,  # 하락추세
            current_price < sma_21  # 하락추세 확인
        ]
        
        if all(buy_conditions):
            return "BUY"
        elif any(sell_conditions):
            return "SELL"
        else:
            return "HOLD"


class Backtester:
    """백테스팅 엔진"""
    
    def __init__(self, initial_capital: float = 1000.0, risk_reward_ratio: float = 2.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_reward_ratio = risk_reward_ratio
        self.strategy = TradingStrategy(risk_reward_ratio)
        self.trades = []
        self.position = None  # None, 'LONG', 'SHORT'
        self.entry_price = None
        self.entry_time = None
    
    def run_simulation(self, price_data: List[Dict], symbol: str = 'SOL') -> Dict:
        """시뮬레이션 실행"""
        logger.info(f"Starting backtest for {symbol}...")
        
        for i in range(21, len(price_data)):  # 21 캔들부터 시작
            # 매매 신호 생성
            signal = self.strategy.generate_signals(price_data[:i+1])
            
            current_price = price_data[i]['price']
            timestamp = price_data[i]['timestamp']
            
            # 매매 로직
            self.execute_trade(signal, current_price, timestamp, symbol)
            
            # 보유 중인지 체크 후 청산
            self.check_exit(current_price, timestamp)
        
        # 마지막 청산
        self.close_position(price_data[-1]['price'], price_data[-1]['timestamp'])
        
        # 결과 계산
        return self.calculate_results()
    
    def execute_trade(self, signal: str, price: float, timestamp: datetime, symbol: str):
        """거래 실행"""
        if signal == "BUY" and self.position is None:
            # 롱 진입
            risk_amount = self.capital * 0.02  # 2% 리스크
            position_size = risk_amount / self.strategy.stop_loss_pct
            
            self.position = 'LONG'
            self.entry_price = price
            self.entry_time = timestamp
            self.capital -= position_size  # 자금 사용
            
            logger.info(f"📈 BUY {symbol} @ ${price:.4f} | Size: ${position_size:.2f}")
        
        elif signal == "SELL" and self.position is None:
            # 숏 진입
            risk_amount = self.capital * 0.02  # 2% 리스크
            position_size = risk_amount / self.strategy.stop_loss_pct
            
            self.position = 'SHORT'
            self.entry_price = price
            self.entry_time = timestamp
            self.capital -= position_size  # 자금 사용
            
            logger.info(f"📉 SELL {symbol} @ ${price:.4f} | Size: ${position_size:.2f}")
    
    def check_exit(self, current_price: float, timestamp: datetime):
        """청산 조건 체크"""
        if self.position is None:
            return
        
        if self.position == 'LONG':
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            
            # 스탑로스 체크
            if pnl_pct <= -self.strategy.stop_loss_pct:
                self.close_position(current_price, timestamp, reason="STOP_LOSS")
            
            # 타겟 체크
            elif pnl_pct >= self.strategy.take_profit_pct:
                self.close_position(current_price, timestamp, reason="TAKE_PROFIT")
        
        elif self.position == 'SHORT':
            pnl_pct = (self.entry_price - current_price) / self.entry_price
            
            # 스탑로스 체크
            if pnl_pct <= -self.strategy.stop_loss_pct:
                self.close_position(current_price, timestamp, reason="STOP_LOSS")
            
            # 타겟 체크
            elif pnl_pct >= self.strategy.take_profit_pct:
                self.close_position(current_price, timestamp, reason="TAKE_PROFIT")
    
    def close_position(self, exit_price: float, timestamp: datetime, reason: str = "MANUAL"):
        """포지션 청산"""
        if self.position is None:
            return
        
        if self.position == 'LONG':
            pnl_pct = (exit_price - self.entry_price) / self.entry_price
            pnl_amount = self.entry_price * pnl_pct * (self.capital / self.entry_price)
        else:  # SHORT
            pnl_pct = (self.entry_price - exit_price) / self.entry_price
            pnl_amount = self.entry_price * pnl_pct * (self.capital / self.entry_price)
        
        # 자금 복귀
        position_size = self.entry_price / self.strategy.stop_loss_pct * 0.02
        self.capital += position_size + pnl_amount
        
        trade = {
            'position': self.position,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'entry_time': self.entry_time,
            'exit_time': timestamp,
            'reason': reason
        }
        
        self.trades.append(trade)
        
        logger.info(f"💰 CLOSE {self.position} @ ${exit_price:.4f} | PnL: {pnl_pct*100:+.2f}% (${pnl_amount:+.2f}) | {reason}")
        
        # 포지션 리셋
        self.position = None
        self.entry_price = None
        self.entry_time = None
    
    def calculate_results(self) -> Dict:
        """결과 계산"""
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        losing_trades = len([t for t in self.trades if t['pnl_pct'] < 0])
        
        total_pnl = sum(t['pnl_amount'] for t in self.trades)
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 손익비 계산
        winning_pnls = [abs(t['pnl_pct']) for t in self.trades if t['pnl_pct'] > 0]
        losing_pnls = [abs(t['pnl_pct']) for t in self.trades if t['pnl_pct'] < 0]
        
        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        actual_risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 손실 컷오프 횟수
        stop_losses = len([t for t in self.trades if t['reason'] == "STOP_LOSS"])
        take_profits = len([t for t in self.trades if t['reason'] == "TAKE_PROFIT"])
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'actual_risk_reward': actual_risk_reward,
            'stop_losses': stop_losses,
            'take_profits': take_profits,
            'target_risk_reward': self.risk_reward_ratio
        }
        
        return results
    
    def print_results(self, results: Dict, symbol: str = 'SOL'):
        """결과 출력"""
        logger.info("\n" + "="*60)
        logger.info(f"📊 BACKTEST RESULTS - {symbol}")
        logger.info("="*60)
        logger.info(f"Initial Capital:  ${results['initial_capital']:.2f}")
        logger.info(f"Final Capital:    ${results['final_capital']:.2f}")
        logger.info(f"Total Return:     {results['total_return']:+.2f}%")
        logger.info(f"Total PnL:       ${results['total_pnl']:+.2f}")
        logger.info("")
        logger.info(f"Total Trades:     {results['total_trades']}")
        logger.info(f"Winning Trades:   {results['winning_trades']} ({results['win_rate']:.1f}%)")
        logger.info(f"Losing Trades:   {results['losing_trades']}")
        logger.info("")
        logger.info(f"Avg Win:         {results['avg_win']:.2f}%")
        logger.info(f"Avg Loss:        {results['avg_loss']:.2f}%")
        logger.info(f"Actual Risk/Reward: {results['actual_risk_reward']:.2f}x")
        logger.info(f"Target Risk/Reward: {results['target_risk_reward']:.2f}x")
        logger.info("")
        logger.info(f"Stop Losses:     {results['stop_losses']}")
        logger.info(f"Take Profits:    {results['take_profits']}")
        logger.info("="*60)


def generate_mock_data(symbol: str = 'SOL', days: int = 30) -> List[Dict]:
    """모의 데이터 생성 (테스트용)"""
    data = []
    base_price = 89.0
    current_price = base_price
    
    start_time = datetime.now()
    
    for i in range(days * 24):  # 24개 캔들/일
        # 랜덤 가격 변동
        change_pct = random.uniform(-0.03, 0.03)  # ±3% 변동
        current_price *= (1 + change_pct)
        
        # 추세 추가 (50% 확률 상승, 50% 하락)
        if random.random() > 0.5:
            trend = random.uniform(0.0001, 0.0005)  # 상승추세
        else:
            trend = random.uniform(-0.0005, -0.0001)  # 하락추세
        
        current_price *= (1 + trend)
        
        data.append({
            'symbol': symbol,
            'price': current_price,
            'timestamp': start_time + timedelta(hours=i)
        })
    
    return data


def main():
    """메인 실행"""
    # 모의 데이터 생성 (30일, 24캔들/일)
    logger.info("Generating mock price data...")
    mock_data = generate_mock_data('SOL', days=30)
    logger.info(f"Generated {len(mock_data)} price candles\n")
    
    # 백테스팅 실행
    backtester = Backtester(initial_capital=1000.0, risk_reward_ratio=2.0)
    results = backtester.run_simulation(mock_data, 'SOL')
    
    # 결과 출력
    backtester.print_results(results, 'SOL')
    
    # 결과 저장
    with open('backtest_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to backtest_results.json")


if __name__ == "__main__":
    main()
