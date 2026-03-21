# 🚀 실전 전환 가이드 - Real-Time Trading Bot

---

## ⚠️ **CRITICAL SECURITY WARNING** ⚠️

**API 키가 노출되었습니다!**
- 제공하신 API Key: `qn7piY14...`
- 제공하신 API Secret: `Z0uwjG8qX...`

**즉시 조치 사항:**
1. 바이낸스 메뉴에서 현재 API 키 **즉시 삭제/변경**하세요.
2. 새로운 API 키를 생성하세요.
3. 제3자에게 절대 API 키를 공개하지 마세요.
4. 아래 코드는 테스트용이며, 실전 사용 시 자금 손실 책임은 전적으로 사용자에게 있습니다.

---

## 📦 필요한 패키지 설치

### 1️⃣ 방법 A: pipx (권장)
```bash
# pipx 설치 (이미 설치되어 있다면 스킵)
brew install pipx

# ccxt 설치
pipx install ccxt

# websockets 설치 (필수)
pipx install websockets
```

### 2️⃣ 방법 B: 가상 환경 (venv)
```bash
# 가상 환경 생성
cd /tmp/solana-trader
python3 -m venv venv

# 가상 환경 활성화
source venv/bin/activate

# ccxt 설치
pip install ccxt

# websockets 설치
pip install websockets
```

### 3️⃣ 방법 C: 시스템 패키지 (비권장)
```bash
# Homebrew로 ccxt 설치
brew install ccxt

# websockets 설치
pip install websockets --break-system-packages --user
```

---

## 🚀 실전 봇 실행 방법

### 1️⃣ 환경 설정

#### API 키 설정
```bash
# .env 파일 생성 (보안을 위해 강력 권장)
cat > .env <<EOF
BINANCE_API_KEY=your_new_api_key_here
BINANCE_API_SECRET=your_new_api_secret_here
EOF

# 또는 코드에 직접 설정 (비권장, 테스트용)
# 파일: realtime_trading_bot.py
# 줄 16~17 수정:
BINANCE_API_KEY = "qn7piY14..."
BINANCE_API_SECRET = "Z0uwjG8qX..."
```

#### 거래 파라미터 설정 (필요시 수정)
```python
# 파일: realtime_trading_bot.py
# 줄 24~30 수정:

SYMBOLS = ['SOLUSDT']  # 1개만 테스트 (SOL)
INITIAL_CAPITAL = 100.0    # $100 테스트 (모든 자금 잃으면 안전)
RISK_PERCENT = 0.01      # 1% 손실 (더 보수적)
TAKE_PROFIT_PERCENT = 0.02 # 2% 이익 (더 보수적)
RISK_REWARD_RATIO = 2.0    # 1:2 손익비
MAX_POSITIONS = 1        # 1개만 보유 (더 보수적)
```

---

### 2️⃣ 실전 실행 (Paper Trading 먼저!)

#### A. Paper Trading (권장 - 안전)
```bash
# ccxt 설치 확인
pip3 list | grep ccxt

# Paper Trading 모드로 실행
# (코드에서 주문을 실제로 내지 않고 로그만 찍음)
# 아직 코드가 실제 주문을 내지 않음을 확인하고 싶다면:
python3 realtime_trading_bot.py
```

#### B. 실전 Money Trading (매우 위험)
```bash
# 실전 전 필히 체크리스트 완료되었는지 확인:
# [ ] API 키 변경 완료
# [ ] 손실 한도 설정 (예: $10 미만)
# [ ] 테스트 모드에서 충분히 검증 완료
# [ ] 감당할 수준의 자금만 사용

# 실전 실행 (자금이 모두 사라질 수 있음!)
python3 realtime_trading_bot.py
```

---

## 📊 실전 전환 체크리스트

### [ ] 1. API 키 보안
- [ ] 기존 API 키 삭제/변경
- [ ] 새로운 API 키 생성
- [ ] API 키 절대 공유 금지

### [ ] 2. 환경 설정
- [ ] ccxt 설치 완료
- [ ] websockets 설치 완료
- [ ] .env 파일 생성 완료

### [ ] 3. 거래 파라미터 조정
- [ ] SYMBOLS 설정 (1개부터 시작 권장)
- [ ] INITIAL_CAPITAL 설정 (소액부터 권장, 예: $100)
- [ ] RISK_PERCENT 설정 (낮게, 예: 1%)
- [ ] TAKE_PROFIT_PERCENT 설정 (낮게, 예: 2%)
- [ ] MAX_POSITIONS 설정 (1개부터 권장)

### [ ] 4. 리스크 관리
- [ ] 최대 손실 한도 설정 (예: -$10)
- [ ] 1일 최대 거래 수 설정 (예: 10건)
- [ ] 감당할 자금 비율 설정 (예: 전체의 10%)

### [ ] 5. 테스트
- [ ] Paper Trading 모드 테스트 (1시간)
- [ ] 거래 로그 확인
- [ ] 기술지표 동작 확인
- [ ] 에러 처리 확인

### [ ] 6. 실전 진입 (테스트 후)
- [ ] $100 소액 테스트
- [ ] 모니터링 시작
- [ ] 1시간 뒤 결과 확인

---

## 🚨 위험 경고

### ❌ 하지 말 것
1. **모든 자금 투입** - 최소 $1000부터 시작 권장
2. **최대 포지션 무시** - 1개만 보유 권장
3. **손실 한도 무시** - 최대 -$5 손실 권장
4. **백테스팅 없이 실전** - 최소 1시간 페이퍼 트레이딩 권장

### ✅ 해야 할 것
1. **소액 테스트** - $100으로 시작하여 전략 검증
2. **1일 최대 거래 수 제한** - 예: 10건/일
3. **최대 포지션 수 제한** - 예: 3개
4. **손실 한도 설정** - 예: -$10/거래
5. **거래소 담보 설정** - 페이퍼 트레이딩을 피함

---

## 📊 예상 시나리오

### 최악의 경우 (모두 손실)
- 초기 자본: $1,000
- 거래 10건 × -$10 = -$100 손실
- 최종 자본: $900 (10% 손실)

### 최고의 경우 (모두 이익)
- 초기 자본: $1,000
- 거래 10건 × $20 = $200 이익
- 최종 자본: $1,200 (20% 이익)

### 현실적인 경우 (승률 50%)
- 초기 자본: $1,000
- 거래 10건 (5승/5손) × ($20 - $10) = $50 이익
- 최종 자본: $1,050 (5% 이익)

---

## 🎯 결론

**실전 전환 전 필히 확인하세요:**
- [ ] ccxt 설치 완료
- [ ] websockets 설치 완료
- [ ] API 키 변경 완료 (기존 키 삭제/변경)
- [ ] 소액 테스트 완료 ($100)
- [ ] 리스크 관리 설정 완료
- [ ] 1시간 페이퍼 트레이딩 완료

**준비되었나요?**
- ccxt 설치: `pip install ccxt`
- 실행: `python3 realtime_trading_bot.py`

**⚠️ 주의:**
이것은 **LIVE MONEY TRADING**입니다. 모든 거래는 실제 자금을 움직입니다. 리스크를 충분히 이해하고, 감당할 수 있는 자금만 사용하세요.

---

**🔗 링크:**
- GitHub Repository: https://github.com/wlstj23207-coder/solana-trading-bot
- 실전 실행 파일: `realtime_trading_bot.py`

---

**어느 것부터 하면 될까요?**
1. `pip install ccxt`?
2. `.env` 파일 설정?
3. 페이퍼 트레이딩 테스트?
4. 바로 실전 실행?

**주의:** 책임은 전적으로 사용자에게 있습니다! 🚀
