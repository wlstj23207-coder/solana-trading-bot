"""
Real-Time Trading Bot - Binance WebSocket
실시간 가격 수집 + 실시간 기술지표 + 실시간 매매
"""

import asyncio
import ccxt.async_support as ccxt
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# 🚨 WARNING: API Keys are hardcoded!
# 🚨 In production, use .env file!
# ========================================
BINANCE_API_KEY = "qn7piY14KZ0uwjG8qXjtBniSIqhHOUNNq52TRshKE8Xi97yMuwQlo67wcbadQX8X"
BINANCE_API_SECRET = "Z0uwjG8qXjtBniSIqhHOUNNq52TRshKE8Xi97yMuwQlo67wcbadQX8X"

# ========================================
# 🎯 Trading Parameters
# ========================================
SYMBOLS = ['SOLUSDT', 'BONKUSDT', 'WIFUSDT', 'JUPUSDT']
INITIAL_CAPITAL = 1000.0
RISK_PERCENT = 0.015  # 1.5% 손실
TAKE_PROFIT_PERCENT = 0.030  # 3.0% 이익
RISK_REWARD_RATIO = TAKE_PROFIT_PERCENT / RISK_PERCENT  # 1:2 손익비
MAX_POSITIONS = 3

# 기술지표 파라미터
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
BB_PERIOD = 20
BB_STD_DEV = 2.0
RSI_PERIOD = 14

# ========================================
# 📊 Technical Indicators
# ========================================

class TechnicalIndicators:
    """기술지표 계산"""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """EMA 계산"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_macd(prices: List[float], 
                        fast_period: int = 12,
                        slow_period: int = 26,
                        signal_period: int = 9) -> Tuple[float, float, float]:
        """MACD 계산"""
        
        if len(prices) < slow_period + 1:
            return (0.0, 0.0, 0.0)
        
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow_period)
        
        macd_line = ema_fast - ema_slow
        
        # 시그널 EMA
        if len(macd_line) < signal_period:
            return (macd_line, 0.0, 0.0)
        
        ema_signal = TechnicalIndicators.calculate_ema(macd_line, signal_period)
        histogram = macd_line - ema_signal
        
        return (macd_line, ema_signal, histogram)
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], 
                                  period: int = 20,
                                  std_dev_multiplier: float = 2.0) -> Tuple[float, float, float]:
        """볼린저 밴드 계산"""
        
        if len(prices) < period:
            return (0.0, 0.0, 0.0)
        
        sma = sum(prices[-period:]) / period
        
        # 표준편차 계산
        squared_diffs = [(p - sma) ** 2 for p in prices[-period:]]
        variance = sum(squared_diffs) / period
        std_dev = math.sqrt(variance)
        
        upper_band = sma + (std_dev_multiplier * std_dev)
        lower_band = sma - (std_dev_multiplier * std_dev)
        
        return (upper_band, sma, lower_band)
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
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

# ========================================
# 🤖 Binance WebSocket Client
# ========================================

class BinanceRealTimeTrader:
    """Binance 실시간 트레이더"""
    
    def __init__(self):
        self.positions = {}  # {symbol: position_info}
        self.trades = []
        self.capital = INITIAL_CAPITAL
        
        # 가격 이력 (기술지표 계산용)
        self.price_history = {symbol: [] for symbol in SYMBOLS}
        
        # ccxt async client
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Use Futures API for lower latency
            }
        })
        
        # WebSocket URL (공식)
        self.ws_url = "wss://stream.binance.com:9443/ws"
        
        # WebSocket 연결
        self.ws = None
        
        # 실시간 가격
        self.current_prices = {}
    
    async def connect_websocket(self):
        """WebSocket 연결"""
        try:
            # Create streams
            streams = []
            for symbol in SYMBOLS:
                symbol_lower = symbol.lower().replace('usdt', '')
                streams.append(f"{symbol_lower}@kline_1m")
            
            streams = "/".join(streams)
            full_url = f"{self.ws_url}/{streams}"
            
            import websockets
            
            self.ws = await websockets.connect(full_url)
            logger.info(f"✅ WebSocket connected to {full_url}")
            
            return self.ws
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            return None
    
    async def process_kline_stream(self, symbol: str, message: Dict):
        """K-line 스트림 처리"""
        try:
            kline = message.get('k', {})
            close_price = float(kline.get('c', 0))
            open_price = float(kline.get('o', 0))
            high_price = float(kline.get('h', 0))
            low_price = float(kline.get('l', 0))
            volume = float(kline.get('v', 0))
            
            # 가격 업데이트
            self.current_prices[symbol] = close_price
            
            # 가격 이력 추가 (기술지표 계산용)
            self.price_history[symbol].append(close_price)
            
            # 최대 100개 캔들 유지
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]
            
            # 기술지표 계산
            self.calculate_indicators_and_trade(symbol)
            
        except Exception as e:
            logger.error(f"❌ Error processing {symbol} kline: {e}")
    
    def calculate_indicators_and_trade(self, symbol: str):
        """기술지표 계산 및 매매"""
        try:
            prices = self.price_history[symbol]
            
            if len(prices) < 50:
                return
            
            # 기술지표 계산
            macd_line, macd_signal, macd_histogram = TechnicalIndicators.calculate_macd(
                prices, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD
            )
            
            upper_band, middle_band, lower_band = TechnicalIndicators.calculate_bollinger_bands(
                prices, BB_PERIOD, BB_STD_DEV
            )
            
            rsi = TechnicalIndicators.calculate_rsi(prices, RSI_PERIOD)
            
            # MACD 분석
            macd_bullish = macd_line > macd_signal and macd_histogram > 0
            macd_bearish = macd_line < macd_signal and macd_histogram < 0
            
            # 볼린저 밴드 분석
            in_lower_band = self.current_prices[symbol] <= lower_band
            in_upper_band = self.current_prices[symbol] >= upper_band
            
            # RSI 분석
            oversold = rsi < 30
            overbought = rsi > 70
            
            # 매매 신호 생성 (공격적 전략)
            long_conditions = [
                macd_bullish and in_lower_band and oversold,
                macd_bullish and rsi < 40,
                in_lower_band and rsi < 30
            ]
            
            short_conditions = [
                macd_bearish and in_upper_band and overbought,
                macd_bearish and rsi > 60,
                in_upper_band and rsi > 70
            ]
            
            long_signal_count = sum(1 for cond in long_conditions if cond)
            short_signal_count = sum(1 for cond in short_conditions if cond)
            
            # 매매 신호 체크
            if long_signal_count >= 2 and symbol not in self.positions:
                self.execute_order(symbol, 'BUY', self.current_prices[symbol])
            
            elif short_signal_count >= 2 and symbol not in self.positions:
                self.execute_order(symbol, 'SELL', self.current_prices[symbol])
            
            # 청산 조건 체크
            self.check_exit_conditions(symbol, macd_line, macd_signal, upper_band, lower_band)
            
        except Exception as e:
            logger.error(f"❌ Error calculating indicators for {symbol}: {e}")
    
    def check_exit_conditions(self, symbol: str, macd_line: float, macd_signal: float, 
                            upper_band: float, lower_band: float):
        """청산 조건 체크"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        current_price = self.current_prices[symbol]
        
        macd_bearish = macd_line < macd_signal
        macd_bullish = macd_line > macd_signal
        
        if position['side'] == 'BUY':
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            # 스탑로스 체크
            if pnl_pct <= -RISK_PERCENT:
                self.close_position(symbol, current_price, 'STOP_LOSS')
            
            # 타겟 이익 체크
            elif pnl_pct >= TAKE_PROFIT_PERCENT:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
            
            # 볼린저 밴드 청산 (보수적)
            elif current_price >= upper_band:
                self.close_position(symbol, current_price, 'BOLLINGER_EXIT')
            
            # MACD 하락추세 청산 (보수적)
            elif macd_bearish and pnl_pct > 0:
                self.close_position(symbol, current_price, 'MACD_DIVERGENCE')
        
        elif position['side'] == 'SELL':
            pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
            
            # 스탑로스 체크
            if pnl_pct <= -RISK_PERCENT:
                self.close_position(symbol, current_price, 'STOP_LOSS')
            
            # 타겟 이익 체크
            elif pnl_pct >= TAKE_PROFIT_PERCENT:
                self.close_position(symbol, current_price, 'TAKE_PROFIT')
            
            # 볼린저 밴드 청산 (보수적)
            elif current_price <= lower_band:
                self.close_position(symbol, current_price, 'BOLLINGER_EXIT')
            
            # MACD 상승추세 청산 (보수적)
            elif macd_bullish and pnl_pct > 0:
                self.close_position(symbol, current_price, 'MACD_DIVERGENCE')
    
    async def execute_order(self, symbol: str, side: str, price: float):
        """실제 주문 실행 (CCXT REST API)"""
        try:
            # 최대 포지션 체크
            if len(self.positions) >= MAX_POSITIONS:
                logger.info(f"⚠️ Max positions reached ({MAX_POSITIONS}), skipping {symbol}")
                return
            
            # 거래 금액 계산
            risk_amount = self.capital * RISK_PERCENT
            if side == 'BUY':
                position_size = risk_amount / RISK_PERCENT
                quantity = position_size / price
            else:  # SELL
                position_size = risk_amount / RISK_PERCENT
                quantity = position_size / price
            
            # 주문 실행 (Market Order)
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=quantity
            )
            
            # 포지션 저장
            self.positions[symbol] = {
                'side': side,
                'entry_price': price,
                'size': position_size,
                'stop_loss': price * (1 - RISK_PERCENT) if side == 'BUY' else price * (1 + RISK_PERCENT),
                'take_profit': price * (1 + TAKE_PROFIT_PERCENT) if side == 'BUY' else price * (1 - TAKE_PROFIT_PERCENT),
                'entry_time': datetime.now(),
                'order_id': order['id']
            }
            
            # 자금 업데이트
            self.capital -= position_size
            
            logger.info(f"📈 {'LONG' if side == 'BUY' else 'SHORT'} {symbol} @ ${price:.4f} | Size: ${position_size:.2f} | Order: {order['id']}")
            
        except Exception as e:
            logger.error(f"❌ Order execution failed for {symbol}: {e}")
    
    async def close_position(self, symbol: str, price: float, reason: str):
        """포지션 청산"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        try:
            # 주문 취소 (Market Order으로 청산)
            side = 'SELL' if position['side'] == 'BUY' else 'BUY'
            
            # 실제 남은 수량 계산
            quantity = position['size'] / position['entry_price']
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=quantity
            )
            
            # PnL 계산
            if position['side'] == 'BUY':
                pnl_pct = (price - position['entry_price']) / position['entry_price']
                pnl_amount = position['size'] * pnl_pct
            else:  # SELL
                pnl_pct = (position['entry_price'] - price) / position['entry_price']
                pnl_amount = position['size'] * pnl_pct
            
            # 자금 복귀
            self.capital += position['size'] + pnl_amount
            
            # 거래 기록
            trade = {
                'symbol': symbol,
                'side': position['side'],
                'entry_price': position['entry_price'],
                'exit_price': price,
                'pnl_pct': pnl_pct * 100,
                'pnl_amount': pnl_amount,
                'entry_time': position['entry_time'],
                'exit_time': datetime.now(),
                'reason': reason,
                'order_id': position['order_id'],
                'close_order_id': order['id']
            }
            
            self.trades.append(trade)
            del self.positions[symbol]
            
            logger.info(f"💰 {'CLOSED LONG' if position['side'] == 'BUY' else 'CLOSED SHORT'} {symbol} @ ${price:.4f} | PnL: {pnl_pct*100:+.2f}% (${pnl_amount:+.2f}) | {reason}")
            
        except Exception as e:
            logger.error(f"❌ Failed to close position for {symbol}: {e}")
    
    async def run(self):
        """메인 실행 함수"""
        logger.info("="*80)
        logger.info("🚀 Real-Time Trading Bot - Binance WebSocket")
        logger.info("="*80)
        logger.info("")
        logger.info("🎯 Trading Parameters:")
        logger.info(f"  Symbols: {SYMBOLS}")
        logger.info(f"  Initial Capital: ${INITIAL_CAPITAL:.2f}")
        logger.info(f"  Risk Percent: {RISK_PERCENT*100:.1f}%")
        logger.info(f"  Take Profit: {TAKE_PROFIT_PERCENT*100:.1f}%")
        logger.info(f"  Max Positions: {MAX_POSITIONS}")
        logger.info("")
        logger.info("📊 Technical Indicators:")
        logger.info(f"  MACD: {MACD_FAST_PERIOD}/{MACD_SLOW_PERIOD}/{MACD_SIGNAL_PERIOD}")
        logger.info(f"  Bollinger Bands: {BB_PERIOD} / {BB_STD_DEV}")
        logger.info(f"  RSI: {RSI_PERIOD}")
        logger.info("")
        logger.info("⚠️  Warning: This is LIVE TRADING with REAL MONEY!")
        logger.info("⚠️  Make sure you have enough funds in your account!")
        logger.info("="*80)
        logger.info("")
        
        # WebSocket 연결
        ws = await self.connect_websocket()
        if not ws:
            logger.error("❌ Failed to connect to WebSocket. Exiting...")
            return
        
        # WebSocket 메시지 루프
        async with ws:
            async for message in ws:
                data = json.loads(message)
                stream = data.get('stream')
                
                if stream:
                    # K-line 스트림 처리
                    for symbol in SYMBOLS:
                        if symbol.lower() in stream:
                            await self.process_kline_stream(symbol, data)
                            break
        
        # WebSocket 연결 종료 후 청산
        logger.info("\nClosing all remaining positions...")
        for symbol in list(self.positions.keys()):
            await self.close_position(symbol, self.current_prices.get(symbol, 0.0), "CONNECTION_CLOSED")
        
        # 최종 결과 출력
        self.print_final_results()
    
    def print_final_results(self):
        """최종 결과 출력"""
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        losing_trades = len([t for t in self.trades if t['pnl_pct'] < 0])
        
        total_pnl = sum(t['pnl_amount'] for t in self.trades)
        total_return = ((self.capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
        
        # 코인별 거래
        symbol_trades = {}
        for trade in self.trades:
            symbol = trade['symbol']
            if symbol not in symbol_trades:
                symbol_trades[symbol] = []
            symbol_trades[symbol].append(trade)
        
        logger.info("")
        logger.info("="*80)
        logger.info("📊 FINAL RESULTS - REAL-TIME TRADING")
        logger.info("="*80)
        logger.info(f"Initial Capital:  ${INITIAL_CAPITAL:.2f}")
        logger.info(f"Final Capital:    ${self.capital:.2f}")
        logger.info(f"Total Return:     {total_return:+.2f}%")
        logger.info(f"Total PnL:         ${total_pnl:+.2f}")
        logger.info("")
        logger.info(f"Total Trades:     {total_trades}")
        logger.info(f"Winning Trades:   {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
        logger.info(f"Losing Trades:   {losing_trades}")
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
        results = {
            'summary': {
                'initial_capital': INITIAL_CAPITAL,
                'final_capital': self.capital,
                'total_return': total_return,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'win_rate': winning_trades / total_trades * 100 if total_trades > 0 else 0,
                'max_profit': max([t['pnl_amount'] for t in self.trades]) if self.trades else 0,
                'max_loss': min([t['pnl_amount'] for t in self.trades]) if self.trades else 0
            },
            'by_symbol': {
                symbol: {
                    'trades': len(trades),
                    'pnl': sum(t['pnl_amount'] for t in trades),
                    'win_rate': len([t for t in trades if t['pnl_pct'] > 0]) / len(trades) * 100 if trades else 0
                }
                for symbol, trades in symbol_trades.items()
            },
            'trades': self.trades
        }
        
        with open('realtime_trading_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("\nResults saved to realtime_trading_results.json")

async def main():
    """메인 실행"""
    trader = BinanceRealTimeTrader()
    await trader.run()

if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️ Trading bot stopped by user")
        sys.exit(0)
