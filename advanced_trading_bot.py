"""
Solana Trading Bot (Advanced Version)
MACD + 볼린저 밴드 조합 전략
롱/숏 다중 코인 자동매매
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdvancedTrader:
    """고급 트레이딩 전략 (MACD + 볼린저 밴드)"""
    
    def __init__(self, initial_capital: float = 1000.0, risk_reward_ratio: float = 2.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_reward_ratio = risk_reward_ratio
        self.stop_loss_pct = 0.02  # 2% 스탑로스
        self.take_profit_pct = self.stop_loss_pct * risk_reward_ratio  # 4% 타겟
        
        # 포지션 관리
        self.positions = {}  # {symbol: position_info}
        
        # 거래 내역
        self.trades = []
        
        # 주요 Solana 코인 리스트
        self.solana_tokens = [
            {
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111112',
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
    
    def calculate_ema(self, prices: List[float], period: int = 12) -> float:
        """EMA 계산"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def calculate_macd(self, prices: List[float], 
                    fast_period: int = 12, 
                    slow_period: int = 26, 
                    signal_period: int = 9) -> tuple:
        """MACD 계산 (이동평균 수렴 발산)"""
        
        if len(prices) < slow_period + 1:
            return (0, 0, 0, 50.0)  # 기본값: macd_line, signal_line, histogram, zero line
        
        # EMA 계산
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)
        
        # MACD 라인 (빠른 EMA - 느린 EMA)
        macd_line = ema_fast - ema_slow
        
        # 시그널 라인 (MACD의 EMA)
        macd_signals = [macd_line]
        if len(macd_signals) >= signal_period:
            # 시그널 EMA 계산
            ema_signal = self.calculate_ema(macd_signals, signal_period)
        else:
            ema_signal = 0
        
        # 히스토그램 (MACD - 시그널)
        histogram = macd_line - ema_signal
        zero_line = 50.0  # 0선
        
        return (macd_line, ema_signal, histogram, zero_line)
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev_multiplier: float = 2.0) -> tuple:
        """볼린저 밴드 계산"""
        if len(prices) < period:
            return (0, 0, 0)  # 기본값: 상단, 중단, 하단
        
        sma = sum(prices[-period:]) / period
        
        # 표준편차 계산
        squared_diffs = [(p - sma) ** 2 for p in prices[-period:]]
        variance = sum(squared_diffs) / period
        std_dev = math.sqrt(variance)
        
        upper_band = sma + (std_dev_multiplier * std_dev)
        lower_band = sma - (std_dev_multiplier * std_dev)
        
        return (upper_band, sma, lower_band)
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산 (상대강도지표)"""
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
    
    def generate_signals(self, price_history: List[Dict], symbol: str) -> Dict:
        """매매 신호 생성 (MACD + 볼린저 밴드 + RSI 조합)"""
        if len(price_history) < 30:
            return {'action': 'HOLD', 'reason': 'Insufficient data (need 30 candles)'}
        
        prices = [p['price'] for p in price_history]
        current_price = prices[-1]
        
        # 기술지표 계산
        macd_line, macd_signal, macd_histogram, macd_zero = self.calculate_macd(prices)
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(prices, period=20, std_dev_multiplier=2.0)
        rsi = self.calculate_rsi(prices, period=14)
        
        # MACD 분석
        macd_bullish = macd_line > macd_signal and macd_histogram > 0  # 상승추세
        macd_bearish = macd_line < macd_signal and macd_histogram < 0  # 하락추세
        
        # 볼린저 밴드 분석
        in_lower_band = current_price <= lower_band  # 하단 밴드 터치
        in_upper_band = current_price >= upper_band  # 상단 밴드 터치
        breakout = current_price < lower_band * 0.98 or current_price > upper_band * 1.02  # 밴드 브레이크아웃
        
        # RSI 분석
        oversold = rsi < 30  # 과매도
        overbought = rsi > 70  # 과매수
        
        # 롱 매수 조건 (강력한 신호 조합)
        long_conditions = [
            # MACD 상승추세 + 볼린저 하단 밴드 (과매도)
            macd_bullish and in_lower_band and oversold,
            # MACD 상승추세 + 볼린저 밴드 브레이크아웃
            macd_bullish and breakout and rsi < 50,
            # 볼린저 하단 터치 + RSI 과매도
            in_lower_band and oversold,
        ]
        
        # 숏 매도 조건 (강력한 신호 조합)
        short_conditions = [
            # MACD 하락추세 + 볼린저 상단 밴드 (과매수)
            macd_bearish and in_upper_band and overbought,
            # MACD 하락추세 + 볼린저 밴드 브레이크아웃
            macd_bearish and breakout and rsi > 50,
            # 볼린저 상단 터치 + RSI 과매수
            in_upper_band and overbought,
        ]
        
        # 조건 수 세기 (최소 2개 만족 시 실행)
        long_signal_count = sum(1 for cond in long_conditions if cond)
        short_signal_count = sum(1 for cond in short_conditions if cond)
        
        if long_signal_count >= 2:
            reasons = []
            if macd_bullish:
                reasons.append("MACD Bullish")
            if in_lower_band:
                reasons.append("Below Lower BB")
            if oversold:
                reasons.append("RSI < 30")
            
            return {
                'action': 'LONG',
                'macd': (macd_line, macd_signal, macd_histogram),
                'bollinger': (upper_band, middle_band, lower_band),
                'rsi': rsi,
                'reason': ' + '.join(reasons)
            }
        
        elif short_signal_count >= 2:
            reasons = []
            if macd_bearish:
                reasons.append("MACD Bearish")
            if in_upper_band:
                reasons.append("Above Upper BB")
            if overbought:
                reasons.append("RSI > 70")
            
            return {
                'action': 'SHORT',
                'macd': (macd_line, macd_signal, macd_histogram),
                'bollinger': (upper_band, middle_band, lower_band),
                'rsi': rsi,
                'reason': ' + '.join(reasons)
            }
        else:
            return {
                'action': 'HOLD',
                'macd': (macd_line, macd_signal, macd_histogram),
                'bollinger': (upper_band, middle_band, lower_band),
                'rsi': rsi,
                'reason': 'No clear signal'
            }
    
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
                    'take_profit': price * (1 + self.take_profit_pct),
                    'indicators_at_entry': {}
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
                    'take_profit': price * (1 - self.take_profit_pct),
                    'indicators_at_entry': {}
                }
                self.capital -= position_size  # 자금 사용
                
                logger.info(f"📉 SHORT {symbol} @ ${price:.4f} | Size: ${position_size:.2f} | SL: ${price*(1+self.stop_loss_pct):.4f} | TP: ${price*(1-self.take_profit_pct):.4f}")
    
    def check_exits(self, current_prices: Dict[str, float]):
        """청산 조건 체크 (전체 포지션)"""
        for symbol, position in list(self.positions.items()):
            current_price = current_prices.get(symbol)
            
            if current_price is None:
                continue
            
            # 현재 기술지표 계산
            price_history = self.get_recent_price_history(symbol)
            if len(price_history) < 30:
                continue
            
            prices = [p['price'] for p in price_history]
            macd_line, macd_signal, macd_histogram, _ = self.calculate_macd(prices)
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(prices, period=20, std_dev_multiplier=2.0)
            
            # 청산 조건
            if position['position'] == 'LONG':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                
                # MACD 하락추세 청산
                macd_bearish = macd_line < macd_signal and macd_histogram < 0
                
                # 스탑로스 체크
                if pnl_pct <= -self.stop_loss_pct:
                    self.close_position(symbol, current_price, "STOP_LOSS")
                # 볼린저 상단 밴드 청산
                elif current_price >= upper_band:
                    self.close_position(symbol, current_price, "BOLLINGER_EXIT")
                # 타겟 체크
                elif pnl_pct >= self.take_profit_pct:
                    self.close_position(symbol, current_price, "TAKE_PROFIT")
                # MACD 하락추세 청산 (보수적)
                elif macd_bearish and pnl_pct > 0 and pnl_pct < self.take_profit_pct * 0.5:
                    self.close_position(symbol, current_price, "MACD_DIVERGENCE")
            
            elif position['position'] == 'SHORT':
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                
                # MACD 상승추세 청산
                macd_bullish = macd_line > macd_signal and macd_histogram > 0
                
                # 스탑로스 체크
                if pnl_pct <= -self.stop_loss_pct:
                    self.close_position(symbol, current_price, "STOP_LOSS")
                # 볼린저 하단 밴드 청산
                elif current_price <= lower_band:
                    self.close_position(symbol, current_price, "BOLLINGER_EXIT")
                # 타겟 체크
                elif pnl_pct >= self.take_profit_pct:
                    self.close_position(symbol, current_price, "TAKE_PROFIT")
                # MACD 상승추세 청산 (보수적)
                elif macd_bullish and pnl_pct > 0 and pnl_pct < self.take_profit_pct * 0.5:
                    self.close_position(symbol, current_price, "MACD_DIVERGENCE")
    
    def get_recent_price_history(self, symbol: str, max_length: int = 50) -> List[Dict]:
        """최근 가격 이력 반환"""
        history = []
        for trade in reversed(self.trades):
            if trade['symbol'] == symbol:
                history.append({
                    'symbol': symbol,
                    'price': trade['entry_price'],
                    'timestamp': trade['entry_time']
                })
                history.append({
                    'symbol': symbol,
                    'price': trade['exit_price'],
                    'timestamp': trade['exit_time']
                })
        
        # 최근 거래부터
        return history[:max_length]
    
    def close_position(self, symbol: str, exit_price: float, reason: str = "MANUAL"):
        """포지션 청산"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # PnL 계산 (청산 시 필요)
        if position['position'] == 'LONG':
            pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
            pnl_amount = position['size'] * pnl_pct
        else:  # SHORT
            pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
            pnl_amount = position['size'] * pnl_pct
        
        # 자금 복귀
        self.capital += position['size'] + pnl_amount
        
        # MACD 계산 (청산 시 필요)
        exit_macd = self.calculate_macd([position['entry_price'], exit_price])[0] if len([position['entry_price'], exit_price]) >= 2 else (0, 0, 0)
        
        # 볼린저 밴드 계산 (청산 시 필요)
        exit_bollinger = self.calculate_bollinger_bands([position['entry_price'], exit_price])[0] if len([position['entry_price'], exit_price]) >= 20 else (0, 0, 0)
        
        # RSI 계산 (청산 시 필요)
        exit_rsi = self.calculate_rsi([position['entry_price']], 14) if len([position['entry_price'], exit_price]) >= 1 else 50.0
        
        trade = {
            'symbol': symbol,
            'position': position['position'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now(),
            'reason': reason,
            'exit_macd': exit_macd,
            'exit_bollinger': exit_bollinger,
            'exit_rsi': exit_rsi
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


def generate_mock_data_advanced() -> Dict[str, List[Dict]]:
    """고급 모의 데이터 생성 (안정적인 추세 + 가격 변동성)"""
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
        
        # 추세 정의 (상승/하락 주기)
        if random.random() > 0.5:
            trend_direction = 1  # 상승추세
            trend_strength = random.uniform(0.001, 0.003)  # 0.1% ~ 0.3% 기간당
        else:
            trend_direction = -1  # 하락추세
            trend_strength = random.uniform(-0.003, -0.001)  # -0.3% ~ -0.1% 기간당
        
        for i in range(30 * 24):  # 24개 캔들/일
            # 추세 변동
            change = trend_direction * trend_strength
            
            # 주기적인 추세 전환 (3일마다)
            if i % 72 == 0:
                trend_direction *= -1
            
            current_price = current_price * (1 + change)
            
            # 랜덤 노이즈 (변동성 있는 코인은 더 높음)
            if symbol == 'WIF':
                noise_pct = random.uniform(-0.08, 0.08)  # ±8%
            elif symbol == 'BONK':
                noise_pct = random.uniform(-0.12, 0.12)  # ±12%
            elif symbol == 'SOL':
                noise_pct = random.uniform(-0.05, 0.05)  # ±5%
            else:
                noise_pct = random.uniform(-0.06, 0.06)  # ±6%
            
            current_price = current_price * (1 + noise_pct)
            
            token_data.append({
                'symbol': symbol,
                'price': current_price,
                'timestamp': start_time + timedelta(hours=i)
            })
        
        data[symbol] = token_data
    
    return data


def main():
    """메인 실행 - MACD + 볼린저 밴드 + RSI 조합 전략"""
    logger.info("="*80)
    logger.info("🚀 Advanced Multi-Coin Trading Bot")
    logger.info("="*80)
    logger.info("")
    logger.info("전략: MACD + 볼린저 밴드 + RSI 조합")
    logger.info("- MACD: 이동평균 수렴 발산 (12/26/9)")
    logger.info("- 볼린저 밴드: 20기간, 2표준편차")
    logger.info("- RSI: 상대강도지표 (14기간)")
    logger.info("- 매수 조건: MACD 상승추세 + 볼린저 하단 밴드 + RSI 과매도 (최소 2개)")
    logger.info("- 매도 조건: MACD 하락추세 + 볼린저 상단 밴드 + RSI 과매수 (최소 2개)")
    logger.info("- 손익비: 2% 스탑로스 / 4% 타겟 (1:2)")
    logger.info("- 최대 포지션: 3개")
    logger.info("")
    logger.info("⚠️  주의: 이것은 테스트 모드입니다. 실전 사용 전 필히 백테스팅 필요!")
    logger.info("="*80)
    logger.info("")
    
    # 모의 데이터 생성
    logger.info("Generating advanced mock price data for 5 coins...")
    all_data = generate_mock_data_advanced()
    
    # 트레이더 초기화
    trader = AdvancedTrader(initial_capital=1000.0, risk_reward_ratio=2.0)
    
    logger.info(f"Initial Capital: ${trader.get_capital():.2f}")
    logger.info("")
    
    # 시뮬레이션 실행 (720 캔들 = 30일)
    logger.info("Starting backtest simulation (30 days)...")
    
    for i in range(30, 720):  # 30 캔들부터 (데이터 누적)
        
        # 현재 가격 수집
        current_prices = {symbol: data[i]['price'] for symbol, data in all_data.items()}
        
        # 각 코인별 신호 생성 및 매매
        for symbol in ['SOL', 'BONK', 'WIF', 'JUP', 'RAY']:
            price_history = all_data[symbol][:i+1]
            signal = trader.generate_signals(price_history, symbol)
            
            current_price = current_prices[symbol]
            current_time = datetime.now()
            
            # 신호에 따라 매매
            if signal['action'] in ['LONG', 'SHORT'] and symbol not in trader.positions:
                trader.execute_trade(symbol, signal['action'], current_price, current_time)
        
        # 청산 체크 (3캔들마다)
        if i % 3 == 0:
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
    
    # 청산 원인 통계
    reasons_count = {}
    for trade in trader.trades:
        reason = trade['reason']
        if reason not in reasons_count:
            reasons_count[reason] = []
        reasons_count[reason].append(trade)
    
    # 손익비 계산
    winning_pnls = [abs(t['pnl_pct']) for t in trader.trades if t['pnl_pct'] > 0]
    losing_pnls = [abs(t['pnl_pct']) for t in trader.trades if t['pnl_pct'] < 0]
    
    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
    actual_risk_reward = avg_win / avg_loss if avg_loss > 0 else 0
    
    # 스탑로스/타겟 횟수
    stop_losses = len([t for t in trader.trades if t['reason'] == "STOP_LOSS"])
    take_profits = len([t for t in trader.trades if t['reason'] == "TAKE_PROFIT"])
    bollinger_exits = len([t for t in trader.trades if t['reason'] == "BOLLINGER_EXIT"])
    macd_divergence_exits = len([t for t in trader.trades if t['reason'] == "MACD_DIVERGENCE"])
    
    # 코인별 거래
    symbol_trades = {}
    for trade in trader.trades:
        symbol = trade['symbol']
        if symbol not in symbol_trades:
            symbol_trades[symbol] = []
        symbol_trades[symbol].append(trade)
    
    logger.info("")
    logger.info("="*80)
    logger.info("📊 FINAL RESULTS - ADVANCED TRADING")
    logger.info("="*80)
    logger.info(f"Initial Capital:  ${results['initial_capital']:.2f}")
    logger.info(f"Final Capital:     ${results['final_capital']:.2f}")
    logger.info(f"Total Return:      {total_return:+.2f}%")
    logger.info(f"Total PnL:         ${total_pnl:+.2f}")
    logger.info("")
    logger.info(f"Total Trades:      {results['total_trades']}")
    logger.info(f"Winning Trades:   {winning_trades} ({win_rate:.1f}%)")
    logger.info(f"Losing Trades:     {losing_trades}")
    logger.info("")
    logger.info(f"Avg Win:           {avg_win*100:.2f}%")
    logger.info(f"Avg Loss:          {avg_loss*100:.2f}%")
    logger.info(f"Actual Risk/Reward: {actual_risk_reward:.2f}x")
    logger.info(f"Target Risk/Reward: {trader.risk_reward_ratio:.2f}x")
    logger.info("")
    logger.info("청산 원인:")
    logger.info(f"  Stop Loss:       {stop_losses}")
    logger.info(f"  Take Profit:     {take_profits}")
    logger.info(f"  Bollinger Exit:  {bollinger_exits}")
    logger.info(f"  MACD Divergence: {macd_divergence_exits}")
    logger.info("")
    logger.info(f"Max Profit:         ${max_profit:+.2f}")
    logger.info(f"Max Loss:          ${max_loss:+.2f}")
    logger.info("")
    
    # 코인별 결과
    logger.info("Coin-by-Coin Results:")
    for symbol, trades in symbol_trades.items():
        if trades:
            coin_pnl = sum(t['pnl_amount'] for t in trades)
            coin_trades_count = len(trades)
            coin_wins = len([t for t in trades if t['pnl_pct'] > 0])
            coin_win_rate = (coin_wins / coin_trades_count * 100) if coin_trades_count > 0 else 0
            
            logger.info(f"  {symbol}: {coin_trades_count} trades | {coin_win_rate:.1f}% win rate | ${coin_pnl:+.2f} PnL")
    
    logger.info("="*80)
    
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
        'exit_reasons': reasons_count,
        'by_symbol': {
            symbol: {
                'trades': len(trades),
                'pnl': sum(t['pnl_amount'] for t in trades),
                'win_rate': coin_win_rate if trades else 0
            }
            for symbol, trades in symbol_trades.items()
        },
        'trades': results['trades']
    }
    
    with open('advanced_trading_results.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to advanced_trading_results.json")


if __name__ == "__main__":
    main()
