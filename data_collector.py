"""
Solana Data Collector Module
실시간 Solana 코인 가격 데이터 수집
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import urllib.request

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolanaDataCollector:
    """Solana 데이터 수집기"""
    
    def __init__(self):
        self.price_data = []
        self.running = False
        
        # 주요 Solana 코인 리스트
        self.solana_tokens = [
            {
                'symbol': 'SOL',
                'address': 'So11111111111111111111111111111111111111111112',
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
    
    async def __aenter__(self):
        """Async context manager enter"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def fetch_binance_price(self, symbol: str = 'SOLUSDT') -> Optional[Dict]:
        """Binance에서 실시간 가격 조회"""
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    'symbol': data['symbol'],
                    'price': float(data['price']),
                    'timestamp': datetime.now(timezone.utc)
                }
        except Exception as e:
            logger.error(f"Binance fetch error: {e}")
            return None
    
    def fetch_jupiter_price(self, token_address: str) -> Optional[Dict]:
        """Jupiter Aggregator에서 가격 조회"""
        url = f"https://price.jup.ag/v6/price?ids={token_address}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('data'):
                    price_info = data['data'][token_address]
                    return {
                        'address': token_address,
                        'price': float(price_info.get('price', 0)),
                        'timestamp': datetime.now(timezone.utc)
                    }
        except Exception as e:
            logger.error(f"Jupiter fetch error for {token_address[:8]}...: {e}")
            return None
    
    def collect_all_prices(self) -> List[Dict]:
        """모든 토큰 가격 수집"""
        prices = []
        
        # Binance SOL/USDT
        binance_result = self.fetch_binance_price('SOLUSDT')
        if binance_result:
            prices.append(binance_result)
        
        # Jupiter DEX 토큰들
        for token in self.solana_tokens[1:]:  # SOL 제외
            jupiter_result = self.fetch_jupiter_price(token['address'])
            if jupiter_result:
                prices.append(jupiter_result)
        
        return prices
    
    def continuous_collection(self, interval: int = 5):
        """지속적인 데이터 수집 (초 단위)"""
        self.running = True
        logger.info(f"Starting continuous collection (interval: {interval}s)")
        
        while self.running:
            try:
                prices = self.collect_all_prices()
                
                if prices:
                    logger.info(f"Collected {len(prices)} price points")
                    
                    # 간단 표시
                    for price in prices:
                        if 'symbol' in price:
                            logger.info(f"  {price['symbol']}: ${price['price']:.6f}")
                        else:
                            token_name = next((t['name'] for t in self.solana_tokens if t['address'] == price['address']), 'Unknown')
                            logger.info(f"  {token_name} (${price['address'][:8]}...): ${price['price']:.6f}")
                    
                    # 저장
                    self.price_data.extend(prices)
                
            except Exception as e:
                logger.error(f"Collection error: {e}")
            
            # 간단 대기
            import time
            time.sleep(interval)
    
    def stop(self):
        """수집 중지"""
        self.running = False
        logger.info("Stopping data collection")
    
    def get_data_dataframe(self):
        """수집된 데이터 반환"""
        # 간단 딕셔너리 리스트 반환
        return self.price_data
    
    def save_to_csv(self, filename: str = 'solana_prices.csv'):
        """CSV로 저장"""
        import csv
        with open(filename, 'w', newline='') as f:
            if self.price_data:
                fieldnames = self.price_data[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.price_data)
                logger.info(f"Saved {len(self.price_data)} price points to {filename}")
            else:
                logger.warning("No price data to save")


def main():
    """테스트 실행"""
    collector = SolanaDataCollector()
    
    # 1회 수집 테스트
    logger.info("=== One-time collection test ===")
    prices = collector.collect_all_prices()
    
    if prices:
        logger.info(f"Collected {len(prices)} prices:")
        for price in prices:
            if 'symbol' in price:
                logger.info(f"  {price['symbol']}: ${price['price']:.6f}")
            else:
                token_name = next((t['name'] for t in collector.solana_tokens if t['address'] == price['address']), 'Unknown')
                logger.info(f"  {token_name} (${price['address'][:8]}...): ${price['price']:.6f}")
    
    # 5초 간격 3회 수집 테스트
    logger.info("\n=== Continuous collection test (3 iterations, 5s interval) ===")
    
    # 수동으로 3회 수집
    for i in range(3):
        logger.info(f"\nIteration {i+1}/3:")
        collector.continuous_collection(interval=5)
        
        if i < 2:  # 마지막은 안 멈춤
            import time
            time.sleep(5)
        else:
            collector.stop()
    
    # 결과 저장
    if collector.price_data:
        collector.save_to_csv('test_solana_prices.csv')


if __name__ == "__main__":
    main()
