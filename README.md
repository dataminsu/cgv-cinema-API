<div align="center">

# 🎬 cgv-cinema-API

**CGV 상영시간표·잔여좌석을 위한 비공식 Python 클라이언트 + HTTP API + 예매 알림 모니터**

특화 기능: **CGV 용산아이파크몰**(`siteNo=0013`)의 **토이 스토리 5 · 일반관 2D · 일요일 11시 부근**
예매가 *열리는 순간* / *잔여좌석이 생기는 순간* 을 **정각 기준 5분마다** 감시하여 **이메일로 알림**.

</div>

---

> [!WARNING]
> **비공식(Unofficial).** CGV는 공개 API를 제공하지 않습니다. 이 프로젝트는 2024년 차세대 개편
> 이후 `cgv.co.kr`(Next.js)가 내부적으로 사용하는 사설 JSON API(`api.cgv.co.kr`)를 호출합니다.
> CJ CGV와 무관하며, 개인적·교육적 용도로 합리적인 요청 빈도(예: 5분 간격)로만 사용하세요.
> CGV가 사이트를 다시 개편하면 동작이 깨질 수 있습니다(특히 HMAC 시크릿 회전 시 — 아래 참고).

## 무엇을 하나

- **클라이언트** (`cgv_cinema`): 서명(HMAC) 처리 + 극장/날짜별 상영정보, 극장 목록, 상영일 목록 조회. **표준 라이브러리만** 사용(설치 불필요).
- **HTTP API** (`api/server.py`, FastAPI): 위 기능을 `/showtimes`, `/toystory5`, `/monitor/status` 등 엔드포인트로 노출. Swagger UI 제공.
- **알림 모니터** (`scripts/monitor_toystory5.py`): 정각 기준 N분마다 폴링 → **예매 오픈** 또는 **잔여좌석 발생** 감지 시 콘솔/소리 + **이메일** 알림.

## 동작 원리 (역추적한 API)

| 항목 | 값 |
|---|---|
| 베이스 | `https://api.cgv.co.kr` |
| 상영정보 | `GET /cnm/atkt/searchMovScnInfo?coCd=A420&siteNo=0013&scnYmd=YYYYMMDD&scnsNo=&scnSseq=&rtctlScopCd=08&custNo=` |
| 인증 | `X-TIMESTAMP`(epoch초) + `X-SIGNATURE` = `Base64(HMAC_SHA256("<ts>\|<pathname>\|<body>", SECRET))` |
| 서명 대상 | **pathname만**(쿼리스트링 제외), GET이면 body=`""` |
| 용산아이파크몰 | `siteNo=0013` (씨네드쉐프 용산 `P013` 아님) |

서명이 없으면 `401 {"statusCode":"401","statusMessage":"401 Unauthorized1"}` 가 돌아옵니다.

### 응답 필드 매핑

| 의미 | JSON 키 |
|---|---|
| 영화명(국문/영문) | `movNm` / `movEnm` |
| 상영 시작/종료 | `scnsrtTm` / `scnendTm` (HHMM) |
| 상영관 | `scnsNm` |
| 포맷(표시명) | `movkndDsplNm` (`2D`, `IMAX LASER 2D`, `ULTRA 4DX 2D`, `SCREENX …`) |
| 등급코드 | `scnsGradCd` (`0101`=일반2D, `0201`=4DX, `0301`=IMAX, `0401`=SCREENX, `0105/0106`=씨네드쉐프, `0112`=아트하우스) |
| 총좌석 / **잔여좌석** | `stcnt` / **`frSeatCnt`** |
| 회차 | `scnSseq` |

## 설치

```bash
git clone https://github.com/<your-account>/cgv-cinema-API.git
cd cgv-cinema-API
# 클라이언트/모니터만 쓰면 설치 불필요(표준 라이브러리). API 서버를 쓸 때만:
pip install -r requirements.txt
```

## 빠른 시작

```bash
# 다가오는 일요일 토이스토리5 일반관 2D 회차 조회
python examples/quickstart.py
```

```python
from cgv_cinema import CGVClient, config, filters

client = CGVClient()
date = filters.next_sunday().strftime("%Y%m%d")
shows = client.get_showtimes(config.YONGSAN_IPARK_SITE_NO, date)

for s in filters.general_2d(filters.filter_movie(shows)):
    print(s.start_hhmm, s.hall, f"잔여 {s.free_seats}/{s.total_seats}")
```

## 알림 모니터 (핵심 기능)

```bash
# 지금 상태만 1회 확인 (예매 열렸나? 좌석 있나?)
python scripts/monitor_toystory5.py --once

# 정각 기준 5분마다 감시 (Ctrl+C 종료)
python scripts/monitor_toystory5.py

# 옵션
python scripts/monitor_toystory5.py --date 20260628 --window 1030-1200
python scripts/monitor_toystory5.py --grade all        # 전체 포맷 감시
python scripts/monitor_toystory5.py --interval 5        # 갱신 간격(분)
python scripts/monitor_toystory5.py --max-alerts 12     # 오픈 후 알림 횟수(기본 12=1시간)
python scripts/monitor_toystory5.py --test-email        # SMTP 스모크 테스트(샘플 1통)
```

기본 감시 대상: **용산아이파크몰 · 토이 스토리 5 · 일반관 2D(`0101`) · 10:30–12:00**.
- **예매 오픈/좌석 감지**: 조건에 맞는 회차에 잔여좌석이 생기면 알림.
- **5분마다 반복**: 좌석이 있는 동안 매 폴링(5분)마다 1통씩, **최대 12통(= 5분 × 12 = 1시간)** 발송 후 중단.
- **매진 → 재오픈 재알림**: 좌석이 0이 되면 카운터를 리셋하고, 다시 열리면 또 최대 12통.
- 발송 횟수는 `--max-alerts` 로 조정.

### 이메일 알림 설정 (SMTP)

`.env.example` → `.env` 로 복사 후 채웁니다. 미설정 시 콘솔/소리 알림만 동작합니다.

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=앱_비밀번호      # Gmail은 앱 비밀번호 사용
ALERT_TO=받는사람@example.com  # 콤마로 여러 명
```

```bash
# bash
set -a; . ./.env; set +a
python scripts/monitor_toystory5.py
```

## HTTP API 서버

```bash
pip install -r requirements.txt
uvicorn api.server:app --port 8000     # http://localhost:8000/docs
```

| 메서드·경로 | 설명 |
|---|---|
| `GET /health` | 헬스체크 |
| `GET /sites?q=용산` | 극장 목록(이름 부분일치) |
| `GET /showtimes?site_no=0013&date=YYYYMMDD` | 극장·날짜 전체 상영정보 |
| `GET /toystory5?date=&grade=0101&window=1030-1200` | 토이스토리5 필터 조회 |
| `GET /monitor/status` | "일반관 2D 11시 부근" 예매 오픈/좌석 여부 |

```bash
curl "http://localhost:8000/monitor/status"
# → {"booking_open": false, "seats_available": false, ...}  (아직 안 열림)
```

## 상시 구동 (선택)

- **Windows 작업 스케줄러**: `python scripts/monitor_toystory5.py --once` 를 5분마다 실행하도록 트리거 등록(이 경우 프로그램 자체 루프 대신 OS 스케줄러가 5분 간격 담당).
- **무중단 루프**: 그냥 `python scripts/monitor_toystory5.py` 를 백그라운드로 띄워두면 정각 기준 5분 간격으로 자체 폴링.

## HMAC 시크릿이 막히면 (401 지속)

CGV가 클라이언트 시크릿을 회전했을 수 있습니다. 다음에서 새 값을 추출해
`cgv_cinema/config.py` 의 `HMAC_SECRET` 를 갱신하세요.

```
https://cdn.cgv.co.kr/cgvpomscontent/static/script/<build>/_next/static/chunks/1453-*.js
→ 청크에서  HmacSHA256(r,"....")  의 문자열
```

## 라이선스

[MIT](LICENSE). 비공식 프로젝트이며 CJ CGV와 제휴/보증 관계가 없습니다.
상표·저작권은 각 권리자에게 있습니다.
