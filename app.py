# 쉬운 스윙 스캐너 최종본 — 일목균형표 + 미국 성장주 추세 + 단타
# 실행: streamlit run app.py
# requirements.txt (한 줄에 하나씩): streamlit / yfinance>=0.2.60 / plotly / pandas / numpy / requests / lxml
import io
import time
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

st.set_page_config(page_title="쉬운 스윙 스캐너", page_icon="📈", layout="wide")
NY, KST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")

# ---------------------------------------------------------------- (선택) 비밀번호
try:
    _pw = st.secrets.get("APP_PASSWORD")
except Exception:
    _pw = None
if _pw:
    if st.session_state.get("auth") is not True:
        inp = st.text_input("비밀번호", type="password")
        if inp == _pw:
            st.session_state["auth"] = True
            st.rerun()
        st.stop()

# ================================================================ 종목 유니버스
THEMES = {
    "반도체": "NVDA AMD AVGO TSM ASML MU ARM MRVL AMAT LRCX KLAC INTC QCOM TXN ON MPWR ALAB CRDO COHR LITE SNPS CDNS TER SMCI WDC STX ENTG NXPI ADI MCHP SWKS QRVO GFS UMC LSCC RMBS MTSI AMKR ONTO FORM ACLS POWI SITM AEHR CAMT NVMI PLAB VSH AMBA SLAB DIOD",
    "AI·소프트웨어": "MSFT GOOGL AMZN META ORCL PLTR CRWV NBIS APP SNOW NOW CRM ADBE DDOG CRWD PANW PATH AI NET ZS MDB TEAM TTD GTLB S ESTC HUBS DOCN IBM INTU SOUN BBAI FTNT WDAY OKTA CYBR TENB QLYS MNDY TWLO DT CFLT PCOR APPF PEGA DOCU SHOP TYL FICO VEEV",
    "데이터센터·전력인프라": "VRT MOD NVT TT JCI CARR LII AAON FIX ETN ANET EQIX DLR PWR EME STRL DELL HPE CLS APH GLW HUBB POWL GNRC FLEX JBL CIEN VIAV CSCO IRM AMT WMS BLDR PSTG NTAP ATKR MYRG PRIM IESC",
    "에너지·원전": "CEG VST NRG TLN GEV OKLO SMR NNE CCJ LEU BWXT BE FLNC FSLR ENPH NEE SO DUK ETR XOM CVX OXY SLB AEP D EXC PEG SRE AES RUN NXT EOSE PLUG LNG EQT COP EOG FANG HAL UEC UUUU MPC VLO PSX KMI WMB OKE TRGP DVN",
    "우주·방산·로봇": "TSLA RKLB ASTS LUNR RDW PL SATS KTOS JOBY ACHR LMT NOC ISRG AVAV HWM RTX GD HII LDOS TDY BA GE SERV RR IRDM VSAT TDG AXON ROK EMR ZBRA CGNX",
    "핀테크·크립토": "COIN HOOD MSTR XYZ PYPL SOFI AFRM UPST MARA RIOT CLSK IREN CORZ CIFR HUT GLXY V MA FI FIS NU DKNG TOST",
    "바이오·헬스": "LLY NVO VRTX REGN DXCM ABBV AMGN GILD MRNA ALNY ARGX BMRN INCY NBIX EXAS INSM SMMT RVMD CRSP BEAM HIMS PODD TMDX GKOS INSP ALGN ZTS IDXX MEDP NTRA TEM RXRX",
    "소비·플랫폼": "AAPL NFLX UBER ABNB DASH SPOT RBLX DUOL CAVA CMG SBUX NKE LULU ONON DECK CELH MNST WING ELF TJX COST WMT BKNG MELI SE CPNG LYV RCL CCL NCLH TKO DKS RH",
    "산업·금융·원자재": "CAT DE URI PH ITW GWW FAST PCAR ODFL SAIA XPO SPGI MCO MSCI ICE CME NDAQ BX KKR APO ARES GS MS JPM BAC WFC C SCHW IBKR LPLA FCX NUE STLD AA SCCO MP ALB NEM AEM WPM FNV KGC",
    "퀀텀·신기술": "IONQ RGTI QBTS QUBT LAES EVLV KULR RZLV",
}
THEMES = {k: list(dict.fromkeys(v.split())) for k, v in THEMES.items()}
THEME_OF = {}
for _th, _ts in THEMES.items():
    for _t in _ts:
        THEME_OF.setdefault(_t, _th)

ETFS = ("SPY QQQ DIA IWM MDY IJR VTI SMH SOXX XLK IGV VGT ARKK ARKW ARKG ARKQ ARKX UFO XLE XOP OIH XLU URA URNM TAN GRID PAVE LIT "
        "XME COPX GDX GDXJ SLV GLD XLF KRE XLV IBB XBI XLI ITA XAR XLC XLY XLP XLB ITB XHB JETS EEM FXI KWEB EWJ EWY INDA IBIT").split()

FALLBACK = ("AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA LLY JPM V UNH XOM MA COST HD PG JNJ ABBV WMT NFLX BAC CRM ORCL CVX KO MRK AMD "
            "PEP TMO ADBE LIN ACN MCD CSCO ABT WFC DIS GE TXN INTU QCOM VZ CAT AMGN IBM ISRG NOW DHR GS UBER AMAT BKNG RTX LOW NEE "
            "UNP HON AXP BLK PGR SYK TJX LMT COP VRTX BSX ETN C ADI MU PLD MMC SBUX GILD DE KLAC LRCX PANW ANET CMG SNPS CDNS").split()

WIKI = {
    "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "나스닥 100": "https://en.wikipedia.org/wiki/Nasdaq-100",
    "S&P 400 (중형주)": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "S&P 600 (소형주)": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}
SCOPES = list(WIKI) + ["테마 성장주", "ETF"]

KO_ALIAS = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT", "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "넷플릭스": "NFLX", "팔란티어": "PLTR", "브로드컴": "AVGO", "마이크론": "MU",
    "인텔": "INTC", "에이엠디": "AMD", "퀄컴": "QCOM", "코인베이스": "COIN", "마이크로스트래티지": "MSTR",
    "로빈후드": "HOOD", "아이온큐": "IONQ", "로켓랩": "RKLB", "슈퍼마이크로": "SMCI", "오라클": "ORCL",
    "일라이릴리": "LLY", "노보노디스크": "NVO", "비자": "V", "마스터카드": "MA", "제이피모건": "JPM",
    "코스트코": "COST", "월마트": "WMT", "디즈니": "DIS", "우버": "UBER", "에어비앤비": "ABNB",
    "스노우플레이크": "SNOW", "크라우드스트라이크": "CRWD", "로블록스": "RBLX", "대만반도체": "TSM", "티에스엠씨": "TSM",
    "암홀딩스": "ARM", "소파이": "SOFI", "리게티": "RGTI", "오클로": "OKLO", "비스트라": "VST",
}


@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_index(name: str) -> pd.DataFrame:
    html = requests.get(WIKI[name], headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
    for t in pd.read_html(io.StringIO(html)):
        tcol = next((c for c in t.columns if str(c) in ("Symbol", "Ticker")), None)
        if tcol is None or len(t) < 30:
            continue
        ncol = next((c for c in t.columns if str(c) in ("Security", "Company")), None)
        return pd.DataFrame({
            "ticker": t[tcol].astype(str).str.replace(".", "-", regex=False).str.strip(),
            "이름": t[ncol].astype(str) if ncol is not None else "",
        })
    raise ValueError("표를 찾지 못했습니다")  # 실패는 캐시되지 않음


def fetch_index(name: str) -> pd.DataFrame:
    """위키 목록. 실패하면 10분간 재시도를 멈춰 화면이 느려지지 않게 함"""
    empty = pd.DataFrame(columns=["ticker", "이름"])
    fail = st.session_state.setdefault("_wiki_fail", {})
    if time.time() - fail.get(name, 0) < 600:
        return empty
    try:
        return _fetch_index(name)
    except Exception:
        fail[name] = time.time()
        return empty


def build_universe(sel, extra=""):
    fr = []
    for nm in WIKI:
        if nm in sel:
            f = fetch_index(nm)
            if f.empty and nm == "S&P 500":
                f = pd.DataFrame({"ticker": FALLBACK, "이름": ""})
            fr.append(f)
    if "테마 성장주" in sel:
        fr.append(pd.DataFrame({"ticker": list(THEME_OF), "이름": ""}))
    if "ETF" in sel:
        fr.append(pd.DataFrame({"ticker": ETFS, "이름": ""}))
    ex = [x.strip().upper().replace(".", "-") for x in extra.replace("\n", ",").split(",") if x.strip()]
    if ex:
        fr.append(pd.DataFrame({"ticker": ex, "이름": ""}))
    if not fr:
        return pd.DataFrame(columns=["ticker", "이름", "테마"])
    u = pd.concat(fr, ignore_index=True)
    u["이름"] = u["이름"].replace("", np.nan)
    u = u.sort_values("이름", na_position="last").drop_duplicates("ticker").reset_index(drop=True)
    u["테마"] = u["ticker"].map(THEME_OF).fillna("-")
    u["이름"] = u["이름"].fillna(u["ticker"])
    return u


def search_tickers(q: str, uni: pd.DataFrame):
    """티커·회사 이름·한글 별칭으로 후보 찾기"""
    q = q.strip()
    if not q:
        return []
    qu = q.upper().replace(".", "-")
    alias = [v for k, v in KO_ALIAS.items() if q.replace(" ", "") in k]
    exact = [qu] if qu in set(uni["ticker"]) else []
    names = []
    if len(q) >= 2 and len(uni):
        names = uni.loc[uni["이름"].str.contains(q, case=False, regex=False, na=False), "ticker"].tolist()[:15]
    raw_ok = [qu] if (not exact and qu.isascii() and qu.replace("-", "").isalnum() and len(qu) <= 6) else []
    return list(dict.fromkeys(alias + exact + names + raw_ok))


# ================================================================ 데이터 (실패는 캐시하지 않음)
def _clean(df, intraday=False):
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in cols):
        return None
    df = df[cols].dropna()
    if len(df) == 0:
        return None
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert(NY).tz_localize(None) if intraday else idx.tz_localize(None)
    df = df.set_axis(idx)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if intraday:
        df = df.between_time("09:30", "15:59")
    return df if len(df) else None


def _split(raw, tickers, intraday=False):
    """yfinance 버전에 따라 다른 열 구조를 종목별 표로 나눔"""
    out = {}
    if raw is None or len(raw) == 0:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = set(raw.columns.get_level_values(0))
        lv1 = set(raw.columns.get_level_values(1))
        price_first = "Close" in lv0
        for t in tickers:
            sub = None
            try:
                if price_first and t in lv1:
                    sub = raw.xs(t, axis=1, level=1)
                elif not price_first and t in lv0:
                    sub = raw[t]
            except Exception:
                sub = None
            c = _clean(sub, intraday) if sub is not None else None
            if c is not None:
                out[t] = c
        if not out and len(tickers) == 1:
            c = _clean(raw, intraday)
            if c is not None:
                out[tickers[0]] = c
    else:
        c = _clean(raw, intraday)
        if c is not None and tickers:
            out[tickers[0]] = c
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def _dl_daily(tickers: tuple, period: str) -> dict:
    raw = yf.download(list(tickers), period=period, auto_adjust=True, progress=False, group_by="ticker", threads=True)
    out = _split(raw, list(tickers))
    if not out:
        raise RuntimeError("시세를 받지 못했습니다")  # 예외는 캐시되지 않음
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def _dl_one(ticker: str, period: str) -> pd.DataFrame:
    try:
        out = _split(yf.download(ticker, period=period, auto_adjust=True, progress=False, threads=False), [ticker])
        if ticker in out:
            return out[ticker]
    except Exception:
        pass
    h = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    c = _clean(h)
    if c is None:
        raise ValueError(f"'{ticker}' 시세가 없습니다. 티커를 확인하거나 잠시 후 다시 시도하세요.")
    return c


@st.cache_data(ttl=120, show_spinner=False)
def _dl_intraday(tickers: tuple, period: str) -> dict:
    raw = yf.download(list(tickers), period=period, interval="5m", auto_adjust=True, progress=False,
                      group_by="ticker", threads=True, prepost=False)
    out = _split(raw, list(tickers), intraday=True)
    if not out:
        raise RuntimeError("5분봉을 받지 못했습니다")
    return out


def load_daily(tickers, period, label=""):
    data, errs = {}, []
    bar = st.progress(0.0, text=f"{label} 시세 다운로드 중...")
    n = len(tickers)
    for i in range(0, n, 80):
        chunk = tuple(tickers[i:i + 80])
        for attempt in range(2):
            try:
                data.update(_dl_daily(chunk, period))
                break
            except Exception as e:
                if attempt == 1:
                    errs.append(f"{chunk[0]} 외 {len(chunk) - 1}개: {str(e)[:100]}")
                else:
                    time.sleep(1.5)
        bar.progress(min(i + 80, n) / max(n, 1), text=f"{label} 시세 {min(i + 80, n)}/{n}")
    bar.empty()
    return data, errs


def load_intraday(tickers, period="1mo"):
    data, errs = {}, []
    for i in range(0, len(tickers), 20):
        chunk = tuple(tickers[i:i + 20])
        try:
            data.update(_dl_intraday(chunk, period))
        except Exception as e:
            errs.append(f"{chunk[0]} 외 {len(chunk) - 1}개: {str(e)[:100]}")
    return data, errs


def drop_live_bar(df):
    """장중 미완성 일봉 제거"""
    now = pd.Timestamp.now(tz=NY)
    if len(df) and df.index[-1].date() == now.date() and now.hour < 16:
        return df.iloc[:-1]
    return df


def drop_open_bar(df):
    """진행 중인 5분봉 제거 (닫힌 봉만 사용)"""
    now = pd.Timestamp.now(tz=NY).tz_localize(None)
    if len(df) and df.index[-1] + pd.Timedelta(minutes=5) > now:
        return df.iloc[:-1]
    return df


# ================================================================ 스윙: 8가지 상승 체력 + 진입 타이밍
COND_NAMES = [
    "추세: 종가 > 50일선 > 200일선",
    "장기추세: 200일선이 우상향",
    "일목: 종가가 구름 위",
    "일목: 양운 (선행A > 선행B)",
    "일목: 전환선 > 기준선",
    "강세: 52주 고점 20% 이내",
    "주도주: 3·6개월 수익률이 SPY보다 높음",
    "자금유입: 최근 5일 거래량 ≥ 50일 평균",
]


def feats(raw, spy_close):
    d = raw.copy()
    c, h, l, o, v = d["Close"], d["High"], d["Low"], d["Open"], d["Volume"]
    d["ma50"], d["ma200"] = c.rolling(50).mean(), c.rolling(200).mean()
    d["ema21"] = c.ewm(span=21, adjust=False).mean()
    d["tenkan"] = (h.rolling(9).max() + l.rolling(9).min()) / 2
    d["kijun"] = (h.rolling(26).max() + l.rolling(26).min()) / 2
    d["spanA"] = ((d["tenkan"] + d["kijun"]) / 2).shift(26)
    d["spanB"] = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    d["top"] = d[["spanA", "spanB"]].max(axis=1)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["vol50"] = v.rolling(50).mean()
    hi252 = h.rolling(252, min_periods=200).max()
    s = spy_close.reindex(d.index).ffill()
    r63, r126 = c.pct_change(63), c.pct_change(126)
    d["ret126"] = r126
    d["ex63"] = (r63 - s.pct_change(63)) * 100
    d["ex126"] = (r126 - s.pct_change(126)) * 100
    d["c1"] = (c > d["ma50"]) & (d["ma50"] > d["ma200"])
    d["c2"] = d["ma200"] > d["ma200"].shift(20)
    d["c3"] = c > d["top"]
    d["c4"] = d["spanA"] > d["spanB"]
    d["c5"] = d["tenkan"] > d["kijun"]
    d["c6"] = c >= hi252 * 0.8
    d["c7"] = (r63 > s.pct_change(63)) & (r126 > s.pct_change(126))
    d["c8"] = v.rolling(5).mean() >= d["vol50"]
    d["conds"] = d[[f"c{i}" for i in range(1, 9)]].sum(axis=1)
    d["ext"] = (c / d["kijun"] - 1) * 100
    # 타이밍 ① 돌파: 20일 고점 위 + 거래량 1.3배 + 양봉
    d["brk"] = (c > h.shift(1).rolling(20).max()) & (v >= 1.3 * d["vol50"]) & (c > o)
    # 타이밍 ② 눌림목: 상승 추세 중 21일선 근처까지 쉬고 양봉
    low3 = l.rolling(3).min()
    hi10 = h.rolling(10).max()
    d["pb"] = ((c > d["ema21"]) & (c > o) & (c > c.shift()) & (low3 <= d["ema21"] * 1.02) & (c <= d["ema21"] * 1.05)
               & (d["ema21"] > d["ma50"]) & ((hi10 - low3) / hi10 >= 0.03))
    # 손절가 (손절폭 3~10%로 제한)
    rb = c - 2 * d["atr"]
    rb = pd.Series(np.where(d["kijun"] < c, np.maximum(rb, d["kijun"] * 0.99), rb), index=d.index)
    rp = low3 - 0.3 * d["atr"]
    d["stop_b"] = c - (c - rb).clip(lower=0.03 * c, upper=0.10 * c)
    d["stop_p"] = c - (c - rp).clip(lower=0.03 * c, upper=0.10 * c)
    return d


def summarize(d, mult, min_cond, mkt_ok):
    """마지막 봉 기준 판정·가격 계획"""
    r = d.iloc[-1]
    pb, brk = bool(d["pb"].tail(2).any()), bool(d["brk"].tail(2).any())
    setup = "🎯 눌림목" if pb else ("🚀 돌파" if brk else "-")
    price = float(r["Close"])
    stop = float(r["stop_p"] if pb else r["stop_b"])
    risk = price - stop
    ok_plan = bool(np.isfinite(stop) and risk > 0)
    n = int(r["conds"])
    ext = float(r["ext"]) if pd.notna(r["ext"]) else 0.0
    if n < min_cond:
        status, note = "⚪ 제외", f"상승 체력 {n}/8 (최소 {min_cond})"
    elif setup == "-":
        status, note = "🟡 대기", "눌림목·돌파 타이밍 대기"
    elif ext > 10:
        status, note = "🟡 대기", f"이격 {ext:.0f}% — 추격 주의"
    elif not mkt_ok:
        status, note = "🟡 대기", "시장 약세 — 신규 매수 쉬기"
    else:
        status, note = "🟢 매수후보", "손절가를 미리 걸고 진입"
    return dict(status=status, note=note, setup=setup, n=n, price=price, ext=ext, pb=pb, brk=brk,
                stop=stop if ok_plan else np.nan, target=price + mult * risk if ok_plan else np.nan,
                risk=risk if ok_plan else np.nan, risk_pct=risk / price * 100 if ok_plan else np.nan)


def grade_of(n, rs):
    if n >= 8 and rs >= 80:
        return "A"
    if n >= 7 and rs >= 60:
        return "B"
    return "C"


def shares_for(acct, risk_pct, price, risk):
    if not (risk and risk > 0 and price > 0):
        return 0
    return int(max(0, min(acct * risk_pct / 100 / risk, acct // price)))


@st.cache_data(ttl=600, show_spinner=False)
def market_state():
    out = {}
    for t in ("SPY", "QQQ"):
        raw = drop_live_bar(_dl_one(t, "2y"))
        d = feats(raw, raw["Close"])
        r = d.iloc[-1]
        above50 = bool(r["Close"] > r["ma50"])
        lamp = "🟢" if (above50 and r["Close"] > r["top"]) else ("🟡" if above50 else "🔴")
        out[t] = dict(lamp=lamp, close=float(r["Close"]), ma50=float(r["ma50"]), above50=above50)
    return out


def run_scan(uni, mult, min_cond, mkt_ok):
    spy = drop_live_bar(_dl_one("SPY", "2y"))["Close"]
    data, errs = load_daily(uni["ticker"].tolist(), "2y", "일봉")
    names, themes = dict(zip(uni["ticker"], uni["이름"])), dict(zip(uni["ticker"], uni["테마"]))
    missing = sorted(set(uni["ticker"]) - set(data))
    rows, short = [], []
    with st.spinner("종목별 상승 체력 계산 중..."):
        for t, raw in data.items():
            raw = drop_live_bar(raw)
            if len(raw) < 210:
                short.append(t)
                continue
            try:
                d = feats(raw, spy)
                if pd.isna(d["ret126"].iloc[-1]):
                    continue
                s = summarize(d, mult, min_cond, mkt_ok)
                rows.append({"종목": t, "이름": names.get(t, t), "테마": themes.get(t, "-"), "상태": s["status"],
                             "타이밍": s["setup"], "충족": s["n"], "현재가": s["price"], "손절가": s["stop"],
                             "목표가": s["target"], "손절폭(%)": s["risk_pct"], "이격(%)": s["ext"], "메모": s["note"],
                             "_r126": float(d["ret126"].iloc[-1]), "_bonus": 10 if s["pb"] else (8 if s["brk"] else 0)})
            except Exception:
                continue
    res = pd.DataFrame(rows)
    if res.empty:
        return res, errs, short, missing
    res["RS"] = (res["_r126"].rank(pct=True) * 100).round(0)
    res["등급"] = [grade_of(n, r) for n, r in zip(res["충족"], res["RS"])]
    res["점수"] = (res["충족"] * 10 + res["RS"] * 0.2 + res["_bonus"] - (res["이격(%)"] - 10).clip(lower=0) * 2).round(1)
    for c in ("현재가", "손절가", "목표가"):
        res[c] = res[c].round(2)
    for c in ("손절폭(%)", "이격(%)"):
        res[c] = res[c].round(1)
    res["충족"] = res["충족"].astype(int).astype(str) + "/8"
    return res.drop(columns=["_r126", "_bonus"]), errs, short, missing


# ================================================================ 스윙 승률 검증
def swing_backtest(data, spy, mult, hold, min_cond, use_mkt):
    spy_ok = spy > spy.rolling(50).mean()
    rows = []
    for t, raw in data.items():
        try:
            d = feats(raw, spy)
        except Exception:
            continue
        if len(d) < 260:
            continue
        if use_mkt:
            mk = spy_ok.reindex(d.index).ffill().fillna(False).astype(bool)
        else:
            mk = pd.Series(True, index=d.index)
        base = (d["conds"] >= min_cond) & (d["ext"] <= 10) & mk
        sig = ((d["pb"] | d["brk"]) & base).to_numpy()
        O, H, L, C = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        sp, sb, pbv = d["stop_p"].to_numpy(), d["stop_b"].to_numpy(), d["pb"].to_numpy()
        free = 0
        for i in np.flatnonzero(sig):
            if i < free or i + 1 >= len(d):
                continue
            stop = sp[i] if pbv[i] else sb[i]
            entry = O[i + 1]  # 다음 날 시가에 진입 (미래 정보 사용 방지)
            risk = entry - stop
            if not np.isfinite(risk) or risk <= 0 or risk > 0.15 * entry:
                continue
            tgt = entry + mult * risk
            last = min(i + hold, len(d) - 1)
            ex, why, j_end = C[last], "기간만료", last
            for j in range(i + 1, last + 1):
                if j > i + 1 and O[j] <= stop:
                    ex, why, j_end = O[j], "손절", j
                    break
                if L[j] <= stop:  # 같은 날 손절·목표가 겹치면 손절로 계산 (보수적)
                    ex, why, j_end = stop, "손절", j
                    break
                if H[j] >= tgt:
                    ex, why, j_end = tgt, "목표", j
                    break
            free = j_end + 1
            rows.append({"종목": t, "날짜": d.index[i], "셋업": "눌림목" if pbv[i] else "돌파",
                         "R": round(float((ex - entry) / risk), 2), "수익률(%)": round(float((ex / entry - 1) * 100), 2),
                         "청산": why, "보유일": int(j_end - i)})
    return pd.DataFrame(rows)


def show_stats(B, mult):
    if B is None or B.empty:
        st.info("기간 내 신호가 없었습니다. 상승 체력 최소 개수를 낮추거나 종목 수를 늘려 보세요.")
        return
    n, win, avg = len(B), (B["R"] > 0).mean() * 100, B["R"].mean()
    gp, gl = B.loc[B["R"] > 0, "R"].sum(), -B.loc[B["R"] < 0, "R"].sum()
    pf = gp / gl if gl > 0 else float("inf")
    be = 100 / (1 + mult)
    m = st.columns(5)
    m[0].metric("거래 수", f"{n:,}", help="규칙대로 매매했을 때의 총 거래 횟수. 30회 미만이면 우연일 수 있습니다.")
    m[1].metric("승률", f"{win:.0f}%", help="이익으로 끝난 거래의 비율.")
    m[2].metric("거래당 기대수익", f"{avg:+.2f} R", help="한 번 거래할 때 평균적으로 얻는 결과(R=손절폭). 반드시 + 여야 합니다.")
    m[3].metric("손익분기 승률", f"{be:.0f}%", help="목표 배수에 따라 본전이 되는 승률. 이보다 승률이 높아야 이득입니다.")
    m[4].metric("손익비(PF)", "∞" if pf == float("inf") else f"{pf:.2f}", help="총이익 ÷ 총손실. 1보다 커야 합니다.")
    if n < 30:
        st.warning("거래 수가 30회 미만이라 결과를 믿기 어렵습니다. 종목 수나 기간을 늘려 보세요.")
    if avg >= 0.15:
        st.success(f"승률 {win:.0f}% / 거래당 {avg:+.2f}R — 이 설정은 과거에 통했습니다. (실전은 수수료·슬리피지로 더 나빠집니다)")
    elif avg > 0:
        st.info(f"거래당 {avg:+.2f}R로 이익은 나지만 작습니다. 비용을 빼면 본전일 수 있어요.")
    else:
        st.error(f"거래당 {avg:+.2f}R — 이 설정은 과거에 손해였습니다. 목표 배수·최소 개수를 바꿔 보세요.")
    g1, g2 = st.columns(2)
    g1.write("**셋업별**")
    g1.dataframe(B.groupby("셋업")["R"].agg(거래수="count", 승률=lambda s: (s > 0).mean() * 100, 평균R="mean").round(2))
    g2.write("**청산사유별**")
    g2.dataframe(B.groupby("청산")["R"].agg(거래수="count", 평균R="mean").round(2))
    if pd.api.types.is_datetime64_any_dtype(B["날짜"]):
        yr = B.assign(연도=B["날짜"].dt.year).groupby("연도")["R"].agg(
            거래수="count", 승률=lambda s: (s > 0).mean() * 100, 평균R="mean").round(2)
        st.write("**연도별 (특정 해에만 잘 되는 건 아닌지 확인)**")
        st.dataframe(yr)
    st.write("**누적 R (거래를 시간순으로 더한 값, 우상향이면 규칙이 통했다는 뜻)**")
    st.line_chart(B.sort_values("날짜")["R"].cumsum().reset_index(drop=True))
    with st.expander("전체 거래 내역"):
        st.dataframe(B, hide_index=True)
    st.caption("⚠️ 현재 살아남은 종목으로만 과거를 검증(생존편향)하고 스프레드가 빠져 있어 실제보다 좋게 나옵니다.")


# ================================================================ 스윙 차트·종목 분석
def swing_chart(d, title, stop=None, target=None, ichi_lines=False):
    x = d.tail(200)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03)
    a, b = x["spanA"], x["spanB"]
    for mask, col, nm in ((a >= b, "rgba(239,83,80,0.16)", "양운"), (a < b, "rgba(66,133,244,0.16)", "음운")):
        fig.add_trace(go.Scatter(x=x.index, y=b.where(mask), line=dict(width=0), showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scatter(x=x.index, y=a.where(mask), line=dict(width=0), fill="tonexty", fillcolor=col,
                                 name=nm, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Candlestick(x=x.index, open=x["Open"], high=x["High"], low=x["Low"], close=x["Close"],
                                 increasing_line_color="#ef5350", decreasing_line_color="#1e88e5", name="일봉"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ma50"], line=dict(color="#1565c0", width=1.5), name="50일선"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ma200"], line=dict(color="#757575", width=1.5), name="200일선"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ema21"], line=dict(color="#2e7d32", width=1.2, dash="dot"), name="21일선"), row=1, col=1)
    if ichi_lines:
        fig.add_trace(go.Scatter(x=x.index, y=x["tenkan"], line=dict(color="#fb8c00", width=1), name="전환선"), row=1, col=1)
        fig.add_trace(go.Scatter(x=x.index, y=x["kijun"], line=dict(color="#8e24aa", width=1), name="기준선"), row=1, col=1)
    for col_, nm, clr in (("brk", "🚀 돌파", "#00c853"), ("pb", "🎯 눌림목", "#ff6d00")):
        s = x[x[col_]]
        if len(s):
            fig.add_trace(go.Scatter(x=s.index, y=s["Low"] * 0.97, mode="markers", name=nm,
                                     marker=dict(symbol="triangle-up", size=12, color=clr, line=dict(width=1, color="black"))),
                          row=1, col=1)
    if stop is not None and np.isfinite(stop):
        fig.add_hline(y=stop, line_dash="dash", line_color="#d32f2f", annotation_text=f"손절 {stop:,.2f}", row=1, col=1)
    if target is not None and np.isfinite(target):
        fig.add_hline(y=target, line_dash="dash", line_color="#00897b", annotation_text=f"목표 {target:,.2f}", row=1, col=1)
    vc = np.where(x["Close"] >= x["Open"], "#ef5350", "#1e88e5")
    fig.add_trace(go.Bar(x=x.index, y=x["Volume"], marker_color=vc, name="거래량", showlegend=False), row=2, col=1)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(title=title, height=650, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.07), margin=dict(l=10, r=10, t=80, b=10))
    return fig


def show_stock(ticker, key, ctx):
    """종목 하나 분석: 판정 + 계획 + 차트 + 체크리스트"""
    try:
        raw = drop_live_bar(_dl_one(ticker, "2y"))
        spy = drop_live_bar(_dl_one("SPY", "2y"))["Close"]
    except Exception as e:
        st.error(f"'{ticker}' 데이터를 불러오지 못했습니다: {e}")
        return
    if len(raw) < 80:
        st.error(f"{ticker}: 거래 기간이 너무 짧아(80일 미만) 분석할 수 없습니다.")
        return
    if len(raw) < 210:
        st.warning("상장한 지 오래되지 않아 200일선 계산이 안 됩니다. 추세 조건 일부가 ❌로 나올 수 있습니다.")
    d = feats(raw, spy)
    s = summarize(d, ctx["mult"], ctx["min_cond"], ctx["mkt_ok"])
    r = d.iloc[-1]
    st.markdown(f"### {ticker} · {ctx['names'].get(ticker, ticker)}")
    m = st.columns(5)
    m[0].metric("현재가", f"{s['price']:,.2f}", help="가장 최근 확정 종가")
    m[1].metric("상승 체력", f"{s['n']}/8", help="8가지 조건 중 충족 개수. 7개 이상이면 후보.")
    m[2].metric("매수 타이밍", s["setup"], help="🚀 돌파 / 🎯 눌림목 / - 없음 (최근 2일 기준)")
    m[3].metric("기준선 이격", f"{s['ext']:.1f}%", help="10%를 넘으면 추격 위험")
    ex = r["ex126"]
    m[4].metric("6개월 초과수익", f"{ex:+.0f}%p" if pd.notna(ex) else "-", help="최근 6개월 수익률에서 SPY 수익률을 뺀 값")
    if s["status"].startswith("🟢"):
        st.success(f"🟢 **매수 검토** — {s['setup']} 신호 + 상승 체력 {s['n']}/8. 아래 손절가를 미리 걸고 진입하세요.")
    elif s["status"].startswith("🟡"):
        hi20 = d["High"].shift(1).rolling(20).max().iloc[-1]
        st.info(f"🟡 **대기** — {s['note']}. 참고 가격: 21일선 {r['ema21']:,.2f} · 20일 고점 {hi20:,.2f}")
    else:
        miss = [COND_NAMES[i] for i in range(8) if not bool(r[f"c{i + 1}"])]
        st.warning(f"⚪ **지금은 제외** — {s['note']}. 미충족: " + " / ".join(miss))
    if pd.notna(s["stop"]):
        sh = shares_for(ctx["acct"], ctx["risk_pct"], s["price"], s["risk"])
        p = st.columns(5)
        p[0].metric("진입 참고가", f"{s['price']:,.2f}")
        p[1].metric("손절가", f"{s['stop']:,.2f}", f"-{s['risk_pct']:.1f}%", delta_color="off")
        p[2].metric("목표가", f"{s['target']:,.2f}", f"+{s['risk_pct'] * ctx['mult']:.1f}%", delta_color="off")
        p[3].metric("권장 수량", f"{sh:,}주", help="손절에 걸려도 계좌의 설정 비율만 잃도록 계산")
        p[4].metric("예상 최대손실", f"${sh * s['risk']:,.0f}")
    ich = st.checkbox("전환선·기준선도 보기", False, key=f"{key}_ich")
    st.plotly_chart(swing_chart(d, f"{ticker} 일봉 + 일목 구름 (🚀돌파 / 🎯눌림목 표시)", s["stop"], s["target"], ich),
                    key=f"{key}_chart")
    st.caption("빨강=상승봉 · 파랑=하락봉 · 옅은 띠=일목 구름(빨강 양운/파랑 음운) · 파란선=50일선 · 회색선=200일선 · 초록 점선=21일선")
    st.write("**상승 체력 체크리스트**")
    cl = st.columns(2)
    for i, nm in enumerate(COND_NAMES):
        cl[i % 2].write(("✅ " if bool(r[f"c{i + 1}"]) else "❌ ") + nm)
    with st.expander("📊 이 종목의 과거 신호 검증 (5년)"):
        if st.button("검증 실행", key=f"{key}_bt"):
            try:
                r5, s5 = _dl_one(ticker, "5y"), _dl_one("SPY", "5y")["Close"]
                st.session_state[f"{key}_btres"] = (ticker, swing_backtest(
                    {ticker: drop_live_bar(r5)}, s5, ctx["mult"], ctx["hold"], ctx["min_cond"], ctx["use_mkt"]))
            except Exception as e:
                st.error(f"검증 실패: {e}")
        got = st.session_state.get(f"{key}_btres")
        if got and got[0] == ticker:
            show_stats(got[1], ctx["mult"])


# ================================================================ 단타 (5분봉)
DT_DEFAULT = ("NVDA TSLA AMD PLTR SMCI AVGO META AMZN AAPL MSFT COIN MSTR HOOD SOFI MU ARM APP RKLB IONQ AFRM "
              "UPST SNOW CRWD NFLX UBER SHOP DKNG RIVN MARA RIOT").split()
SESSION = [
    ("09:30", "10:00", "👀 관찰만", "시초 30분: 고점·저점 범위가 만들어지는 중. 사지 않습니다."),
    ("10:00", "11:30", "✅ 가장 좋은 시간", "🚀 시초돌파 · 🎯 VWAP눌림 모두 가능. 신호 대부분이 여기서 나옵니다."),
    ("11:30", "14:00", "⚠️ 점심 구간", "거래량이 줄고 가짜 신호가 늘어납니다. 신규 진입은 쉽니다."),
    ("14:00", "15:30", "✅ 장 후반", "🚀 재돌파 위주. 손절을 짧게, 수량은 평소의 절반."),
    ("15:30", "15:45", "⛔ 신규 금지", "새로 사지 않고 보유분 정리를 준비합니다."),
    ("15:45", "16:00", "🔔 전량 청산", "단타는 밤새 들고 가지 않습니다."),
]


def kst_text(hhmm, base):
    h, m = map(int, hhmm.split(":"))
    t = datetime.combine(base, dtime(h, m), tzinfo=NY).astimezone(KST)
    return t.strftime("%H:%M") + ("(+1일)" if t.date() > base else "")


def dt_prepare(raw):
    d = raw.copy()
    d["day"] = d.index.strftime("%Y-%m-%d")
    g = d.groupby("day", sort=False)
    d["bar"] = g.cumcount()
    tp = (d["High"] + d["Low"] + d["Close"]) / 3
    cv = d["Volume"].groupby(d["day"]).cumsum()
    d["vwap"] = (tp * d["Volume"]).groupby(d["day"]).cumsum() / cv.replace(0, np.nan)
    d["ema9"] = g["Close"].transform(lambda s: s.ewm(span=9, adjust=False).mean())
    pc = d["Close"].shift()
    tr = pd.concat([d["High"] - d["Low"], (d["High"] - pc).abs(), (d["Low"] - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14, min_periods=5).mean()
    # RVOL: 같은 시각까지의 누적 거래량 ÷ 이전 최대 10일 평균
    piv = pd.DataFrame({"day": d["day"], "bar": d["bar"], "cv": cv}).pivot(index="bar", columns="day", values="cv")
    days = list(piv.columns)
    avg = pd.DataFrame(np.nan, index=piv.index, columns=days)
    for k in range(1, len(days)):
        avg[days[k]] = piv[days[max(0, k - 10):k]].mean(axis=1)
    base = avg.to_numpy()[piv.index.get_indexer(d["bar"]), piv.columns.get_indexer(d["day"])]
    safe = np.where(base > 0, base, 1.0)
    d["rvol"] = pd.Series(np.where(base > 0, cv.to_numpy() / safe, np.nan), index=d.index).fillna(1.0)
    dclose = g["Close"].last()
    prev = d["day"].map(dclose.shift())
    d["gap"] = ((g["Open"].transform("first") / prev - 1) * 100).fillna(0.0)
    f6 = d["bar"] < 6
    d["orh"] = d["High"].where(f6).groupby(d["day"]).transform("max")
    d["orl"] = d["Low"].where(f6).groupby(d["day"]).transform("min")
    d["dhi"] = d["High"].groupby(d["day"]).cummax()
    C, O, L = d["Close"], d["Open"], d["Low"]
    bull, up = C > O, (C > d["vwap"]) & (C > d["ema9"])
    above = (C > d["orh"]) & (d["bar"] >= 6)
    fresh = above & ~above.shift(1, fill_value=False)
    orb = fresh & up & bull & (d["rvol"] >= 1.3) & (d["bar"] <= 66) & (d["gap"] > -3)
    vp = ((L.rolling(3).min() <= d["vwap"] * 1.001) & (d["dhi"] / d["vwap"] - 1 >= 0.006)
          & (d["vwap"] > d["vwap"].shift(6)) & up & bull & (C > C.shift())
          & (d["bar"] >= 12) & (d["bar"] <= 66) & (d["rvol"] >= 1.0))
    d["setup"] = np.where(orb, 1, np.where(vp, 2, 0))
    return d


def dt_plan(d, i, mult):
    """신호봉 고가+0.01 돌파 시 진입. 손절=최근 6봉 저점(5분 ATR의 1.5~2.5배로 제한)"""
    trig = round(float(d["High"].iat[i]) + 0.01, 2)
    atr = d["atr"].iat[i]
    atr = float(atr) if pd.notna(atr) and atr > 0 else trig * 0.003
    lowx = float(d["Low"].iloc[max(0, i - 5):i + 1].min())
    risk = float(np.clip(trig - lowx, 1.5 * atr, 2.5 * atr))
    return dict(trig=trig, stop=round(trig - risk, 2), r1=round(trig + risk, 2),
                tgt=round(trig + mult * risk, 2), risk=round(risk, 2))


def dt_backtest(d, mult, cost=0.02):
    rows = []
    H, L, O, C = (d[k].to_numpy() for k in ("High", "Low", "Open", "Close"))
    bar, setup = d["bar"].to_numpy(), d["setup"].to_numpy()
    for day_, idx in d.groupby("day", sort=False).indices.items():
        sig = [i for i in idx if setup[i] > 0]
        if not sig:
            continue
        i, end = sig[0], idx[-1]  # 하루에 첫 신호만 거래
        p = dt_plan(d, i, mult)
        ent = next((j for j in (i + 1, i + 2) if j <= end and H[j] >= p["trig"]), None)  # 2봉 안에 돌파해야 진입
        if ent is None:
            continue
        entry = max(O[ent], p["trig"])
        risk = entry - p["stop"]
        if risk <= 0:
            continue
        tgt, ex, why = entry + mult * risk, C[end], "장마감"
        for k in range(ent, end + 1):
            if bar[k] >= 75:  # 뉴욕 15:45
                ex, why = O[k], "장마감"
                break
            if L[k] <= p["stop"]:
                ex, why = p["stop"], "손절"
                break
            if H[k] >= tgt:
                ex, why = tgt, "목표"
                break
        rows.append({"날짜": pd.Timestamp(day_), "셋업": "시초돌파" if setup[i] == 1 else "VWAP눌림",
                     "진입": round(float(entry), 2), "R": round(float((ex - entry - cost) / risk), 2), "청산": why})
    return pd.DataFrame(rows)


def dt_status(d, mult):
    """마지막 거래일 기준 현재 상태와 계획"""
    day = d["day"].iat[-1]
    idx = np.flatnonzero((d["day"] == day).to_numpy())
    last = d.iloc[-1]
    base = dict(day=day, price=float(last["Close"]), vwap=float(last["vwap"]), rvol=float(last["rvol"]), gap=float(last["gap"]))
    if last["bar"] < 6:
        return dict(base, status="⏳ 범위형성", setup="-", note="시초 30분이 끝나면 판단 (뉴욕 10:00 이후)")
    recent = [i for i in idx[-2:] if d["setup"].iat[i] > 0]
    if recent:
        i = recent[-1]
        kind = "🚀 시초돌파" if d["setup"].iat[i] == 1 else "🎯 VWAP눌림"
        ago = (len(d) - 1 - i) * 5
        when = "방금" if ago == 0 else f"{ago}분 전"
        p = dt_plan(d, i, mult)
        note = f"신호 {when} → 신호봉 고가 {p['trig']} 돌파 시 진입 (2봉 안에 못 넘으면 취소)"
        return dict(base, status=kind, setup=kind, note=note, **p)
    orh = float(last["orh"])
    atr = float(last["atr"]) if pd.notna(last["atr"]) else 0.0
    if last["Close"] > last["vwap"]:
        if last["Close"] > orh + 1.5 * atr:
            note = f"VWAP 위지만 이미 많이 올라 추격 주의. VWAP {last['vwap']:.2f} 까지 눌리면 🎯 대기"
        elif last["Close"] > orh:
            note = f"시초 고점 {orh:.2f} 위에서 진행 중. 새 신호 대기"
        else:
            note = f"시초 고점 {orh:.2f} 돌파 + 거래량 1.3배 대기"
        return dict(base, status="👀 대기", setup="-", note=note)
    return dict(base, status="⚪ 관망", setup="-", note=f"VWAP {last['vwap']:.2f} 아래 — 위로 회복할 때까지 사지 않음")


def dt_chart(d, day, title, plan=None):
    x = d[d["day"] == day]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22], vertical_spacing=0.03)
    orh, orl = x["orh"].iat[0], x["orl"].iat[0]
    if pd.notna(orh) and pd.notna(orl):
        fig.add_hrect(y0=orl, y1=orh, fillcolor="rgba(120,120,120,0.13)", line_width=0, row=1, col=1)
        fig.add_hline(y=orh, line_dash="dot", line_color="gray", annotation_text=f"시초고점 {orh:.2f}", row=1, col=1)
    fig.add_trace(go.Candlestick(x=x.index, open=x["Open"], high=x["High"], low=x["Low"], close=x["Close"],
                                 increasing_line_color="#ef5350", decreasing_line_color="#1e88e5", name="5분봉"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["vwap"], line=dict(color="#fb8c00", width=2), name="VWAP"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x.index, y=x["ema9"], line=dict(color="#8e24aa", width=1.2), name="9EMA"), row=1, col=1)
    for code, nm, clr in ((1, "🚀 시초돌파", "#00c853"), (2, "🎯 VWAP눌림", "#ff6d00")):
        s = x[x["setup"] == code]
        if len(s):
            fig.add_trace(go.Scatter(x=s.index, y=s["Low"] - s["atr"].fillna(0) * 0.5, mode="markers", name=nm,
                                     marker=dict(symbol="triangle-up", size=14, color=clr, line=dict(width=1, color="black"))),
                          row=1, col=1)
    if plan:
        for key_, lab, clr in (("trig", "진입", "#1565c0"), ("stop", "손절", "#d32f2f"), ("r1", "1R", "#43a047"), ("tgt", "목표", "#00897b")):
            fig.add_hline(y=plan[key_], line_dash="dash", line_color=clr, annotation_text=f"{lab} {plan[key_]:.2f}", row=1, col=1)
    vc = np.where(x["Close"] >= x["Open"], "#ef5350", "#1e88e5")
    fig.add_trace(go.Bar(x=x.index, y=x["Volume"], marker_color=vc, name="거래량", showlegend=False), row=2, col=1)
    fig.update_layout(title=title, height=620, xaxis_rangeslider_visible=False,
                      legend=dict(orientation="h", y=1.07), margin=dict(l=10, r=10, t=80, b=10))
    return fig


# ================================================================ 사이드바
with st.sidebar:
    st.title("📈 쉬운 스윙 스캐너")
    scope = st.multiselect("검색할 종목 범위", SCOPES, default=["S&P 500", "나스닥 100", "테마 성장주"],
                           help="S&P500·나스닥100·중소형주는 위키피디아에서 자동으로 불러옵니다. 많이 고를수록 처음 스캔이 오래 걸립니다(약 500종목당 1분).")
    extra = st.text_input("추가 티커 (쉼표로 구분)", "", help="목록에 없는 종목을 직접 추가합니다. 예: PLTR, RKLB")
    st.divider()
    mult = st.slider("목표 수익 (손절폭의 몇 배)", 1.0, 3.0, 1.5, 0.5,
                     help="낮을수록 목표에 빨리 닿아 승률↑, 건당 이익↓. 승률 우선이면 1.0~1.5, 수익 우선이면 2.0~3.0.")
    hold = st.slider("최대 보유일 (승률 검증용)", 5, 40, 15, 5, help="검증에서 이 기간이 지나면 강제 정리한다고 가정. 스윙은 보통 2~4주.")
    min_cond = st.slider("상승 체력 최소 개수 (8개 중)", 5, 8, 7, help="높일수록 후보가 줄고 질이 좋아집니다. 기본 7.")
    use_mkt = st.checkbox("시장이 50일선 위일 때만 매수", True, help="시장이 나쁜 날 나온 신호를 제외합니다. 켜 두는 것을 권장.")
    st.divider()
    acct = st.number_input("투자 가능 금액 ($)", 1000.0, 10_000_000.0, 10000.0, 1000.0, help="권장 수량 계산에 사용")
    risk_pct = st.number_input("1회 감수 손실 (%)", 0.1, 5.0, 1.0, 0.1, help="손절에 걸려도 계좌의 이 비율만 잃도록 수량을 정합니다. (1% 룰)")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.session_state.pop("_wiki_fail", None)
        st.rerun()
    st.caption("무료 시세는 약 15분 지연될 수 있습니다. 교육·참고용이며 투자 판단과 책임은 본인에게 있습니다.")

# ================================================================ 상단: 시장 신호등
try:
    mk = market_state()
except Exception:
    mk = None
mkt_ok = True if (mk is None or not use_mkt) else mk["SPY"]["above50"]
if mk:
    cA, cB, cC = st.columns([1, 1, 3])
    cA.metric("SPY 시장 신호등", mk["SPY"]["lamp"], help="🟢 50일선·구름 모두 위 / 🟡 50일선 위, 구름 위는 아님 / 🔴 50일선 아래")
    cB.metric("QQQ(나스닥)", mk["QQQ"]["lamp"], help="나스닥100 ETF의 같은 기준 신호등")
    if mk["SPY"]["lamp"] == "🔴":
        cC.error("🔴 시장이 약합니다. 신규 매수를 쉬는 것이 승률에 가장 도움이 됩니다.")
    elif mk["SPY"]["lamp"] == "🟡":
        cC.warning("🟡 시장이 애매합니다. A등급 + 🎯눌림목만 소액으로 접근하세요.")
    else:
        cC.success("🟢 시장이 좋습니다. 추천 종목을 적극적으로 확인하세요.")
else:
    st.warning("시장 신호등을 불러오지 못했습니다 (야후 시세 서버 문제일 수 있음). 잠시 후 사이드바의 🔄 새로고침을 눌러 주세요. 그동안 시장 필터는 꺼집니다.")

UNI = build_universe(scope, extra)
ALL_UNI = build_universe(SCOPES, "")
NAMES = dict(zip(ALL_UNI["ticker"], ALL_UNI["이름"]))
NAMES.update(dict(zip(UNI["ticker"], UNI["이름"])))
CTX = dict(mult=mult, hold=hold, min_cond=min_cond, mkt_ok=mkt_ok, use_mkt=use_mkt, acct=acct, risk_pct=risk_pct, names=NAMES)

tab1, tab2, tab3, tab4, tab5, tabG = st.tabs(["🏆 오늘의 추천", "🔍 종목 분석", "⚡ 단타", "✅ 승률 검증", "📖 쉬운 설명", "📚 항목 사전"])

# ================================================================ 탭1: 오늘의 추천
with tab1:
    st.write("버튼 한 번으로 선택한 범위의 종목을 모두 검사해 **오르는 중이면서 지금 살 타이밍인 종목**을 골라냅니다.")
    c1, c2 = st.columns([1, 3])
    top_n = c1.slider("표시 개수", 5, 50, 15, 5)
    c2.caption(f"검사 대상 {len(UNI):,}종목 · 첫 스캔은 1~3분, 이후 30분간 캐시됩니다. 범위는 사이드바에서 바꿀 수 있어요.")
    if st.button("🏆 오늘의 추천 뽑기", type="primary", key="go_scan"):
        if UNI.empty:
            st.error("사이드바에서 검색할 종목 범위를 하나 이상 선택하세요.")
        else:
            try:
                res, errs, short, missing = run_scan(UNI, mult, min_cond, mkt_ok)
                st.session_state["scan"] = dict(res=res, errs=errs, short=short, missing=missing, total=len(UNI),
                                                at=datetime.now(KST).strftime("%m/%d %H:%M"))
                if res.empty:
                    st.session_state["swing_top"] = []
                else:
                    ok = res["충족"].str[0].astype(int) >= min_cond
                    st.session_state["swing_top"] = res[ok].sort_values("점수", ascending=False)["종목"].head(12).tolist()
            except Exception as e:
                st.error(f"스캔 중 오류가 났습니다: {e}")
    S = st.session_state.get("scan")
    if S:
        res = S["res"]
        if res.empty:
            st.error("시세를 받은 종목이 없습니다. 야후 서버가 일시적으로 막혔을 수 있어요. 1~2분 뒤 사이드바 🔄 새로고침 → 다시 뽑기를 눌러 주세요.")
            if S["errs"]:
                st.caption("오류: " + " | ".join(S["errs"][:3]))
        else:
            n_buy = int((res["상태"] == "🟢 매수후보").sum())
            n_wait = int((res["상태"] == "🟡 대기").sum())
            k = st.columns(4)
            k[0].metric("분석 완료", f"{len(res):,}/{S['total']:,}", help="시세를 받아 분석한 종목 수")
            k[1].metric("🟢 매수후보", n_buy, help="체력 + 타이밍 + 시장 필터를 모두 통과")
            k[2].metric("🟡 대기", n_wait, help="체력은 합격, 타이밍/이격/시장이 아직")
            k[3].metric("스캔 시각", S["at"], help="한국 시간 기준")
            order = {"A": 0, "B": 1, "C": 2}
            view_cols = ["종목", "이름", "테마", "등급", "타이밍", "충족", "RS", "현재가", "손절가", "목표가", "손절폭(%)", "이격(%)", "메모"]
            buy = (res[res["상태"] == "🟢 매수후보"].assign(_o=lambda x: x["등급"].map(order))
                   .sort_values(["_o", "점수"], ascending=[True, False]))
            st.subheader(f"🟢 매수후보 TOP {min(top_n, len(buy))}")
            if buy.empty:
                st.info("지금 조건을 모두 통과한 종목이 없습니다. 쉬는 것도 전략입니다. 아래 🟡 대기 목록을 관심종목으로 보세요.")
            else:
                st.dataframe(buy.head(top_n)[view_cols], hide_index=True)
            wait = res[res["상태"] == "🟡 대기"].sort_values("점수", ascending=False)
            with st.expander(f"🟡 대기 종목 {len(wait)}개 (좋은 종목이지만 아직 타이밍 아님)"):
                st.dataframe(wait.head(60)[view_cols], hide_index=True)
            cand = res[res["충족"].str[0].astype(int) >= min_cond]
            th_cnt = cand[cand["테마"] != "-"].groupby("테마")["종목"].count().sort_values(ascending=False)
            if len(th_cnt):
                st.write("**테마별 강세 종목 수** (어느 분야가 강한지)")
                st.bar_chart(th_cnt)
            pool = buy.head(top_n)["종목"].tolist() + wait.head(20)["종목"].tolist()
            if pool:
                st.divider()
                pk = st.selectbox("📈 차트로 볼 종목", pool, format_func=lambda t: f"{t} — {NAMES.get(t, t)}", key="rec_pick")
                show_stock(pk, "rec", CTX)
        if S["missing"] or S["short"] or S["errs"]:
            with st.expander(f"데이터를 못 받았거나 제외된 종목 (시세 없음 {len(S['missing'])} · 상장 짧음 {len(S['short'])})"):
                st.write("시세 없음: " + ", ".join(S["missing"][:80]) + (" ..." if len(S["missing"]) > 80 else ""))
                st.write("상장 1년 미만: " + ", ".join(S["short"][:80]))
                if S["errs"]:
                    st.write("오류 메시지: " + " | ".join(S["errs"][:3]))

# ================================================================ 탭2: 종목 분석
with tab2:
    q = st.text_input("🔍 티커 또는 회사 이름 (예: NVDA, 엔비디아, Palantir)", "NVDA", key="an_q")
    cands = search_tickers(q, ALL_UNI)
    if not cands:
        st.warning("검색 결과가 없습니다. 티커(예: AAPL)나 영문 회사 이름으로 다시 검색해 보세요.")
    else:
        pick = st.selectbox("검색 결과", cands, format_func=lambda t: f"{t} — {NAMES.get(t, '')}", key="an_pick")
        with st.spinner("데이터 불러오는 중..."):
            show_stock(pick, "an", CTX)

# ================================================================ 탭3: 단타
with tab3:
    st.subheader("⚡ 단타 (5분봉) — 하루 안에 끝내는 매매")
    now_ny = datetime.now(NY)
    is_open = now_ny.weekday() < 5 and dtime(9, 30) <= now_ny.time() < dtime(16, 0)
    state_txt = "🟢 개장 중" if is_open else "⚪ 마감 (마지막 거래일 데이터로 연습/복기)"
    st.caption(f"뉴욕 현재 {now_ny:%m/%d %H:%M} · 한국 {datetime.now(KST):%m/%d %H:%M} · 미국장 {state_txt}")
    with st.expander("🕒 시간대별 행동 (한국 시간 자동 환산 · 서머타임 반영)"):
        base_day = now_ny.date()
        tb = pd.DataFrame([{"뉴욕": f"{a}~{b}", "한국": f"{kst_text(a, base_day)}~{kst_text(b, base_day)}", "구분": t, "할 일": w}
                           for a, b, t, w in SESSION])
        st.dataframe(tb, hide_index=True)
    with st.expander("✅ 진입 7단계 (이 순서를 지키세요)"):
        st.markdown("""
1. **시장 신호등**이 🟢·🟡인지 확인 (🔴이면 단타도 쉬기)
2. 종목이 **VWAP 위**에 있는지 확인 (아래면 사지 않음)
3. 신호봉이 **닫힌 뒤**에만 판단 — 🚀 시초 범위 위로 거래량(RVOL 1.3배↑)과 올라선 봉 / 🎯 VWAP까지 눌렸다가 위로 회복한 양봉
4. **신호봉 고가 + 0.01달러**를 넘을 때 매수 (스톱 매수 주문). **2봉(10분) 안에 못 넘으면 취소**
5. 체결 즉시 **손절 주문**을 걸기
6. **1R 도달 시 절반 정리 + 손절을 본전으로 올림**, 나머지는 목표까지
7. 뉴욕 **15:45까지 전량 청산**
""")
    cc = st.columns(3)
    dt_tgt = cc[0].slider("목표 (손절폭의 몇 배)", 1.0, 3.0, 1.5, 0.5, key="dt_tgt", help="1R=손절폭. 단타는 1.0~2.0이 현실적입니다.")
    dt_risk = cc[1].number_input("1회 감수 손실 (%, 단타)", 0.1, 2.0, 0.3, 0.1, key="dt_risk", help="단타는 횟수가 많아 스윙(1%)보다 작게 잡습니다.")
    dt_cost = cc[2].number_input("왕복 비용 ($/주, 검증용)", 0.0, 0.5, 0.02, 0.01, key="dt_cost", help="수수료+슬리피지 가정치. 검증 결과에서 차감됩니다.")
    st.session_state.setdefault("dt_wl", " ".join(DT_DEFAULT))
    s1, s2, s3 = st.tabs(["📡 단타 후보 스캔", "📈 차트 확인·복기", "🧪 단타 검증"])

    with s1:
        st.text_area("후보 티커 (공백/쉼표 구분)", key="dt_wl", height=90,
                     help="거래량이 많고 변동성 있는 종목이 단타에 맞습니다. 직접 고쳐도 됩니다.")

        def _add_swing():
            cur = st.session_state.get("dt_wl", "").replace(",", " ").split()
            st.session_state["dt_wl"] = " ".join(dict.fromkeys(cur + st.session_state.get("swing_top", [])))

        st.button("➕ 오늘의 추천 강세종목 추가", on_click=_add_swing,
                  help="🏆 오늘의 추천에서 뽑힌 일봉 강세 종목을 후보에 넣습니다 (스윙 철학과 결합).")
        wl = list(dict.fromkeys(x.strip().upper().replace(".", "-")
                                for x in st.session_state["dt_wl"].replace(",", " ").split() if x.strip()))[:60]
        if st.button("📡 단타 후보 스캔", type="primary", key="dt_go"):
            with st.spinner(f"{len(wl)}개 종목 5분봉 분석 중..."):
                data5, errs5 = load_intraday(wl, "1mo")
                rows = []
                for t, rw in data5.items():
                    try:
                        d5 = dt_prepare(drop_open_bar(rw))
                        if len(d5) < 20:
                            continue
                        stt = dt_status(d5, dt_tgt)
                        sh = shares_for(acct, dt_risk, stt["price"], stt.get("risk"))
                        rows.append({"종목": t, "상태": stt["status"],
                                     "스윙강세": "✅" if t in st.session_state.get("swing_top", []) else "",
                                     "기준일": stt["day"], "현재가": round(stt["price"], 2), "VWAP": round(stt["vwap"], 2),
                                     "진입(돌파가)": stt.get("trig"), "손절": stt.get("stop"), "1R": stt.get("r1"),
                                     "목표": stt.get("tgt"), "위험($/주)": stt.get("risk"),
                                     "권장수량": sh if stt.get("risk") else None,
                                     "RVOL": round(stt["rvol"], 2), "갭(%)": round(stt["gap"], 1), "메모": stt["note"]})
                    except Exception:
                        continue
            st.session_state["dt_scan"] = (pd.DataFrame(rows), errs5, datetime.now(KST).strftime("%H:%M:%S"))
        D = st.session_state.get("dt_scan")
        if D:
            df5, errs5, at = D
            if df5.empty:
                st.error("5분봉을 받지 못했습니다. 야후 서버가 일시적으로 막혔거나 티커가 잘못됐을 수 있어요. 1~2분 뒤 🔄 새로고침 후 다시 시도하세요.")
                if errs5:
                    st.caption("오류: " + " | ".join(errs5[:2]))
            else:
                rank = {"🚀 시초돌파": 0, "🎯 VWAP눌림": 0, "👀 대기": 1, "⏳ 범위형성": 2, "⚪ 관망": 3}
                df5 = (df5.assign(_o=df5["상태"].map(rank)).sort_values(["_o", "RVOL"], ascending=[True, False])
                       .drop(columns="_o"))
                n_sig = int(df5["상태"].isin(["🚀 시초돌파", "🎯 VWAP눌림"]).sum())
                st.caption(f"스캔 {at} · 신호 {n_sig}개 / 분석 {len(df5)}개 · 마지막 거래일: {df5['기준일'].max()}")
                st.dataframe(df5, hide_index=True)
                st.caption("🚀 시초돌파 · 🎯 VWAP눌림 = 신호(진입가 돌파 시 매수) / 👀 대기 / ⏳ 시초 30분 진행 중 / ⚪ VWAP 아래 관망. 진입·손절 가격은 신호가 있는 종목에만 표시됩니다.")

    with s2:
        t_in = st.text_input("티커", wl[0] if wl else "NVDA", key="dtc_t").strip().upper().replace(".", "-")
        try:
            d5s, _e = load_intraday([t_in], "1mo")
            if t_in not in d5s:
                raise ValueError("5분봉이 없습니다 (티커 확인 또는 잠시 후 재시도)")
            dd = dt_prepare(drop_open_bar(d5s[t_in]))
            days = list(dict.fromkeys(dd["day"]))[::-1]
            day = st.selectbox("날짜 (최근순)", days, key="dtc_day")
            sg = np.flatnonzero((dd["day"] == day).to_numpy() & (dd["setup"].to_numpy() > 0))
            plan = dt_plan(dd, int(sg[-1]), dt_tgt) if len(sg) else None
            st.plotly_chart(dt_chart(dd, day, f"{t_in} 5분봉 · {day}", plan), key="dt_chart")
            st.caption("주황=VWAP · 보라=9EMA · 회색 띠/점선=시초 30분 범위 · 초록▲=🚀 시초돌파 · 주황▲=🎯 VWAP눌림 · 점선=진입/손절/1R/목표")
            if plan:
                sh = shares_for(acct, dt_risk, plan["trig"], plan["risk"])
                pc = st.columns(5)
                pc[0].metric("진입(돌파가)", f"{plan['trig']:.2f}", help="신호봉 고가+0.01. 2봉 안에 넘지 못하면 취소")
                pc[1].metric("손절", f"{plan['stop']:.2f}")
                pc[2].metric("1R(절반 정리)", f"{plan['r1']:.2f}")
                pc[3].metric("목표", f"{plan['tgt']:.2f}")
                pc[4].metric("권장 수량", f"{sh:,}주", help="감수 손실 ÷ 위험($/주), 투자금 한도 내")
            else:
                st.info("이 날은 신호가 없었습니다. 신호 없는 날은 쉬는 것이 정상입니다.")
        except Exception as e:
            st.warning(f"차트를 만들 수 없습니다: {e}")

    with s3:
        st.write("최근 약 1개월 5분봉으로 위 규칙(하루 1회, 첫 신호만)을 그대로 돌려 승률과 거래당 기대수익을 확인합니다.")
        n_t = st.slider("검증 종목 수", 5, 40, 20, 5, key="dt_n", help="후보 티커 목록의 앞에서부터 이 개수만큼 검증합니다.")
        if st.button("🧪 단타 검증 실행", type="primary", key="dt_bt_go"):
            with st.spinner("5분봉 검증 중..."):
                data5, _e = load_intraday(wl[:n_t], "1mo")
                allb = []
                for t, rw in data5.items():
                    try:
                        bt5 = dt_backtest(dt_prepare(drop_open_bar(rw)), dt_tgt, dt_cost)
                        if not bt5.empty:
                            allb.append(bt5.assign(종목=t))
                    except Exception:
                        continue
            st.session_state["dt_bt"] = (pd.concat(allb, ignore_index=True) if allb else pd.DataFrame(), dt_tgt)
        ZD = st.session_state.get("dt_bt")
        if ZD:
            show_stats(ZD[0], ZD[1])
            st.warning("기간이 약 1개월로 짧고 스프레드가 빠져 있어 실제보다 좋게 나옵니다. 단타는 비용 영향이 커서 평균 R이 +0.2 이상은 되어야 의미가 있습니다. 먼저 소액으로 연습하세요.")
    st.info("⚠️ 단타 주의: ① 미국 마진계좌의 당일 매매 횟수 제한(PDT, 계좌 $25,000 기준)이 바뀌는 중이므로 본인 증권사 안내를 확인하세요. "
            "② 손절은 미리 주문으로 걸어 두세요. ③ 하루 손실 한도(계좌의 1%)에 닿으면 그날은 끝냅니다.")

# ================================================================ 탭4: 승률 검증
with tab4:
    st.write("지금 설정(목표 배수·최대 보유일·최소 개수·시장 필터)으로 과거에 매매했다면 어땠는지 확인합니다. **실전 전에 꼭 먼저 보세요.**")
    b1, b2 = st.columns(2)
    n_bt = b1.slider("검증 종목 수", 20, 300, 100, 20, help="선택한 범위에서 무작위로 뽑습니다.")
    per = b2.select_slider("검증 기간", ["3y", "5y", "10y"], "5y")
    if st.button("✅ 승률 검증 실행", type="primary", key="go_bt"):
        if UNI.empty:
            st.error("사이드바에서 종목 범위를 선택하세요.")
        else:
            sample = UNI.sample(min(n_bt, len(UNI)), random_state=1)["ticker"].tolist()
            try:
                spyb = drop_live_bar(_dl_one("SPY", per))["Close"]
                dat, errs = load_daily(sample, per, "검증용")
                with st.spinner("과거 신호 계산 중..."):
                    B = swing_backtest({k: drop_live_bar(v) for k, v in dat.items()}, spyb, mult, hold, min_cond, use_mkt)
                st.session_state["swing_bt"] = (B, len(dat), per)
            except Exception as e:
                st.error(f"검증 중 오류: {e}")
    ZS = st.session_state.get("swing_bt")
    if ZS:
        st.caption(f"{ZS[1]}종목 · {ZS[2]} · 목표 {mult}R · 최대 {hold}일 · 최소 {min_cond}개")
        show_stats(ZS[0], mult)

# ================================================================ 탭5: 쉬운 설명
with tab5:
    st.markdown("""
### 이 앱이 하는 일 (3줄 요약)
1. **오르는 중인 강한 종목만** 골라냅니다. (일목균형표 + 미국 성장주 추세 기준 8가지)
2. 그중 **지금 사도 되는 타이밍**(돌파 / 눌림목)인 종목에 🚀·🎯 표시를 합니다.
3. **손절가·목표가·살 수량**까지 알려줍니다. 단타용 5분봉 신호도 따로 있습니다.

### 8가지 상승 체력 (7개 이상 충족해야 후보)
| 구분 | 조건 | 쉬운 뜻 |
|---|---|---|
| 추세 | 종가 > 50일선 > 200일선 | 단기·장기 모두 오르는 중 |
| 추세 | 200일선 우상향 | 큰 흐름이 상승 |
| 일목 | 종가가 구름 위 | 구름이 지지대 |
| 일목 | 양운 | 구름이 상승 구조 |
| 일목 | 전환선 > 기준선 | 단기 힘이 더 강함 |
| 강세 | 52주 고점 20% 이내 | 신고가 근처, 위 매물 적음 |
| 주도주 | SPY보다 많이 오름 | 시장보다 강한 종목 |
| 자금 | 거래량 증가 | 돈이 들어오는 중 |

### 스윙 매수 타이밍 2가지
- 🚀 **돌파**: 최근 20일 고점을 평소(50일 평균)의 1.3배 이상 거래량으로 넘는 양봉
- 🎯 **눌림목**: 오르던 종목이 21일선 근처까지 쉬었다가 양봉이 나옴 (손절폭이 작아 유리)

### 단타 매수 타이밍 2가지 (5분봉, 뉴욕 10:00~15:00 사이만)
- 🚀 **시초돌파**: 장 시작 30분 고점을 거래량 1.3배↑로 **새로 올라선** 봉 (VWAP·9EMA 위)
- 🎯 **VWAP눌림**: 오른 뒤 VWAP까지 내려왔다가 VWAP·9EMA 위로 올라오는 양봉 (10:30 이후)
- 진입은 **신호봉이 닫힌 뒤, 신호봉 고가+0.01 돌파 시**. 2봉 안에 못 넘으면 취소.

### 승률을 높이는 5가지 습관
1. **시장 신호등이 🔴이면 쉽니다.** 가장 효과가 큰 규칙입니다.
2. **A등급 + 🎯눌림목**부터 봅니다. (손절이 짧고 추격이 아님)
3. **이격이 10% 넘으면 사지 않습니다.** 다음 눌림을 기다립니다.
4. **손절가는 반드시 지킵니다.** 한 번의 큰 손실이 승률 높은 거래를 다 까먹습니다.
5. 한 종목에 계좌의 1%만 잃도록 수량을 정합니다.

### 승률 vs 수익, 꼭 알아둘 점
- **목표 수익 배수를 낮출수록 승률은 올라가지만** 이길 때 이익이 작아집니다.
- 그래서 '승률 검증' 탭의 **승률 + 거래당 기대수익**을 같이 보고 배수를 고르세요.
- 어떤 방법도 수익을 보장하지 않습니다. 앱은 '확률이 좋은 구간'을 찾아주는 도구입니다.

### 하루 사용법
시장 신호등 확인 → 🏆 추천 버튼 → A등급 🎯/🚀 종목을 차트로 확인 → 손절가 주문 걸고 매수
""")
    st.warning("교육·참고용 도구입니다. 투자 판단과 책임은 본인에게 있습니다.")

# ================================================================ 항목 사전
GLOSS = {
    "🚦 시장·상태·점수": [
        ("시장 신호등", "미국 대표지수(SPY)가 오르는 장인지 보여줍니다. 🟢 50일선과 구름 모두 위, 🟡 50일선 위지만 구름 위는 아님, 🔴 50일선 아래.", "🔴이면 신규 매수를 쉬는 것이 승률에 가장 큰 도움이 됩니다."),
        ("상태: 🟢 매수후보", "상승 체력 기준 충족 + 매수 타이밍 신호 + 이격 10% 이하 + 시장 필터 통과.", "A·B등급부터 차트를 확인하세요."),
        ("상태: 🟡 대기", "체력은 합격이지만 타이밍·이격·시장 때문에 아직 아닌 종목. '메모' 열에 이유가 나옵니다.", "관심종목에 담고 눌림이나 돌파를 기다립니다."),
        ("상태: ⚪ 제외", "상승 체력이 최소 개수에 못 미치는 종목.", ""),
        ("등급 (A·B·C)", "A: 체력 8/8 + RS 80 이상 / B: 체력 7개 이상 + RS 60 이상 / C: 그 외.", "A등급 + 🎯 눌림목 조합을 먼저 보세요."),
        ("점수", "충족 개수×10 + RS×0.2 + 타이밍 가산(눌림목 10·돌파 8) − 이격 10% 초과분×2.", "점수 자체보다 '순서'를 보는 용도입니다."),
        ("RS (상대강도)", "최근 6개월 수익률을 이번에 검사한 종목끼리 순위 매긴 값(0~100). 99에 가까울수록 최상위 주도주.", "검사 범위가 바뀌면 RS도 달라집니다."),
        ("충족 (n/8)", "8가지 상승 체력 중 통과한 개수.", "7개 이상이 후보."),
        ("타이밍", "🚀 돌파 또는 🎯 눌림목 신호가 최근 2일 안에 나왔는지.", "'-'는 아직 신호 없음."),
    ],
    "💲 추천표의 가격 항목": [
        ("현재가", "가장 최근 확정 종가.", "장중이면 전일 종가일 수 있습니다."),
        ("손절가", "이 가격 아래로 내려가면 손해를 확정하고 나오는 기준선. 돌파형: (현재가−2×ATR)과 (일목 기준선×0.99) 중 높은 값 / 눌림목형: 최근 3일 저점−0.3×ATR. 손절폭은 3~10%로 제한.", "주문을 미리 걸어 두세요. 손절을 지키는 것이 핵심입니다."),
        ("목표가", "손절폭의 정해진 배수만큼 올랐을 때의 가격 (사이드바 '목표 수익' 배수).", "배수가 낮을수록 빨리 닿아 승률↑, 건당 이익↓."),
        ("손절폭(%)", "현재가에서 손절가까지의 거리.", "클수록 수량을 줄여야 합니다."),
        ("이격(%)", "일목 기준선에서 현재가가 위쪽으로 얼마나 떨어져 있는지.", "10% 넘으면 추격 위험. 다음 눌림을 기다리세요."),
        ("권장 수량", "(투자금×감수 손실%) ÷ (현재가−손절가). 투자금을 넘지 않게 제한.", "'1% 룰'로 한 번 틀려도 계좌가 크게 안 다치게 합니다."),
    ],
    "🎛 사이드바 설정": [
        ("검색할 종목 범위", "S&P500, 나스닥100, 중·소형주, 테마 성장주, ETF 중 검사할 묶음.", "처음엔 기본값으로 충분합니다."),
        ("추가 티커", "목록에 없는 종목을 직접 추가.", "예: PLTR, RKLB"),
        ("목표 수익 (손절폭의 몇 배)", "익절 목표를 정하는 배수 (1.0~3.0).", "승률 우선이면 1.0~1.5, 수익 우선이면 2.0~3.0."),
        ("최대 보유일", "승률 검증에서 이 날짜가 지나면 강제로 정리한다고 가정.", "스윙은 보통 2~4주(10~20일)."),
        ("상승 체력 최소 개수", "8개 중 몇 개 이상 통과해야 후보로 보는지.", "높일수록 후보가 줄고 질이 좋아집니다."),
        ("시장이 50일선 위일 때만 매수", "시장이 나쁜 날 나온 신호를 제외하는 필터.", "켜 두는 것을 권장합니다."),
        ("투자 가능 금액 · 1회 감수 손실", "수량 계산에 쓰는 값. 기본 1% 룰.", "초보는 0.5%부터 시작해도 좋습니다."),
    ],
    "🧱 8가지 상승 체력": [
        ("① 종가 > 50일선 > 200일선", "단기·장기 평균가격보다 모두 위, 단기 평균이 장기 평균보다 높음.", "가장 기본적인 상승 추세 확인."),
        ("② 200일선 우상향", "200일 평균선이 20일 전보다 높음.", "큰 흐름이 상승일 때만 통과."),
        ("③ 종가가 구름 위", "일목 구름이 지지대 역할을 해 줍니다.", "구름 아래 종목은 반등이어도 약한 편."),
        ("④ 양운", "구름의 선행A가 선행B보다 위 = 구름이 상승 구조.", ""),
        ("⑤ 전환선 > 기준선", "단기 힘(9일)이 중기 힘(26일)보다 강함.", "'교차하는 순간'이 아니라 '위에 있는 상태'만 봅니다."),
        ("⑥ 52주 고점 20% 이내", "1년 최고가에 가까운 강한 종목.", "위쪽에 대기 매물이 적습니다."),
        ("⑦ 주도주", "3·6개월 수익률이 모두 SPY보다 높음.", "시장보다 강한 종목만 골라냅니다."),
        ("⑧ 자금 유입", "최근 5일 평균 거래량이 50일 평균 이상.", "돈이 들어오는 종목인지 확인."),
    ],
    "📐 기본 용어": [
        ("50일선·200일선", "최근 50일/200일 종가의 평균선. 각각 중기·장기 추세의 기준.", ""),
        ("21일선(EMA)", "최근 값에 가중치를 둔 21일 평균선. 오르는 종목이 쉬어가는 자리.", "눌림목의 기준선입니다."),
        ("일목 구름", "선행스팬 A·B 사이의 띠. 주가가 위에 있으면 상승, 아래면 약세로 봅니다.", "두꺼울수록 지지·저항이 강합니다."),
        ("전환선·기준선", "각각 9일·26일 고저 평균선. 전환선이 위면 단기 힘이 강합니다.", "기준선은 스윙의 대표적 손절 참고선입니다."),
        ("ATR", "최근 14일 동안 하루 평균 몇 달러 움직였는지(평균 변동폭).", "손절폭을 종목 성격에 맞추는 데 씁니다."),
        ("🚀 돌파 (스윙)", "최근 20일 고점을 50일 평균 거래량의 1.3배 이상으로 넘는 양봉.", "거래량 없는 돌파는 가짜일 확률이 높습니다."),
        ("🎯 눌림목 (스윙)", "21일선 근처(2% 이내)까지 쉬었다가 21일선 위로 마감한 양봉.", "손절폭이 작고 추격매수가 아닙니다."),
        ("R (손절폭 단위)", "손절폭 1개를 1R로 부릅니다. +2R = 손절폭의 2배 이익.", "종목·금액과 상관없이 결과를 비교할 수 있습니다."),
        ("1% 룰", "손절에 걸려도 계좌의 1%만 잃도록 수량을 정하는 방법.", "권장 수량이 자동으로 계산됩니다."),
    ],
    "⚡ 단타 항목": [
        ("5분봉", "5분마다 하나씩 그려지는 캔들. 단타는 이 차트로 판단합니다.", ""),
        ("VWAP", "오늘 거래된 평균 체결단가(거래량 가중). 주황색 선.", "VWAP 위 = 오늘 산 사람 대부분이 이익 → 매수세 우위. 위에서만 삽니다."),
        ("시초 30분 범위", "장 시작 후 30분(5분봉 6개)의 고점·저점. 회색 띠와 점선.", "이 범위를 위로 벗어나는지가 그날 방향의 힌트입니다."),
        ("🚀 시초돌파", "시초 고점 위로 새로 올라선 양봉. 조건: RVOL 1.3배↑, VWAP·9EMA 위 마감, 갭 −3% 이상, 뉴욕 10:00~15:00.", "하루에 첫 신호만 거래합니다."),
        ("🎯 VWAP눌림", "VWAP가 오르는 날 VWAP까지 내려왔다가 VWAP·9EMA 위로 올라오는 양봉. 조건: 당일 고점이 VWAP보다 0.6%↑, 10:30 이후.", "손절이 가까워 손익비가 좋습니다."),
        ("👀 / ⚪ / ⏳", "👀 VWAP 위에서 신호 대기, ⚪ VWAP 아래라 관망, ⏳ 시초 30분 범위 형성 중.", "👀 중 '추격 주의'는 이미 시초 고점을 많이 넘어 올라간 상태입니다."),
        ("진입(돌파가)", "신호봉 고가+0.01. 이 가격을 넘을 때 매수. 2봉(10분) 안에 못 넘으면 신호 취소.", "스톱 매수 주문을 쓰면 편합니다."),
        ("RVOL", "평소 같은 시각까지의 누적 거래량 대비 오늘 거래량 배수.", "1.5배 이상이면 관심이 몰린 날, 1배 미만이면 힘이 약합니다."),
        ("갭(%)", "전일 종가 대비 오늘 시초가의 상승·하락률.", "+갭 + 높은 RVOL이 단타 후보의 기본 조합입니다."),
        ("9EMA", "최근 봉에 가중치를 둔 9봉 평균선(보라색). 단기 힘의 지표.", ""),
        ("손절·1R·목표", "손절 = 최근 6봉 저점 근처(5분봉 ATR의 1.5~2.5배로 제한). 1R = 진입+손절폭, 목표 = 설정한 배수 가격.", "1R에서 절반 정리 후 손절을 본전으로 올리는 방식을 권합니다."),
        ("위험($/주)", "한 주당 손절까지의 금액.", "권장수량 = 감수 손실 ÷ 이 값."),
        ("스윙강세 ✅", "오늘의 추천에서 일봉 상승 체력이 좋게 나온 종목.", "일봉이 강한 종목이 단타도 잘 오르는 편입니다."),
        ("당일 청산", "단타는 밤새 들고 가지 않고 장 마감 전에 정리합니다.", "뉴욕 15:45까지 전량 정리."),
        ("PDT 규정", "미국 마진계좌의 당일 매매 횟수 제한 규정(계좌 $25,000 기준).", "규정이 바뀌는 중이라 증권사 공지를 꼭 확인하세요."),
    ],
    "🧪 승률 검증 용어": [
        ("거래 수", "규칙대로 매매했을 때의 총 거래 횟수.", "30회 미만이면 우연일 수 있습니다."),
        ("승률", "이익으로 끝난 거래 비율.", "승률만 높고 손실이 크면 결국 손해입니다."),
        ("평균 R / 거래당 기대수익", "한 번 거래할 때 평균적으로 얻는 결과.", "반드시 + 인지 확인하세요. 승률보다 더 중요합니다."),
        ("손익분기 승률", "목표 배수에 따라 본전이 되는 승률. 목표 1배면 50%, 1.5배면 40%.", "이보다 승률이 높아야 이득입니다."),
        ("손익비(PF)", "총이익 ÷ 총손실.", "1보다 커야 합니다."),
        ("청산사유", "손절 / 목표 / 기간만료(장마감) 중 어떤 이유로 끝났는지.", ""),
        ("누적 R", "거래 결과(R)를 순서대로 더한 곡선.", "우상향이면 규칙이 꾸준히 통했다는 뜻."),
        ("생존편향", "현재 살아남은 우량 종목만으로 과거를 검증해 결과가 좋게 나오는 착시.", "검증 결과는 실제보다 좋게 나온다고 생각하세요."),
        ("슬리피지", "주문가와 실제 체결가의 차이.", "단타는 비용 영향이 커서 반드시 감안해야 합니다."),
    ],
}

with tabG:
    st.subheader("📚 항목 사전 — 화면에 나오는 말의 뜻")
    kw = st.text_input("찾고 싶은 말 (예: VWAP, 손절, RS)", "", key="gl_kw").strip().lower()
    shown = 0
    for cat, items in GLOSS.items():
        hit = [x for x in items if kw in (x[0] + x[1] + x[2]).lower()]
        if not hit:
            continue
        shown += len(hit)
        with st.expander(cat, expanded=bool(kw)):
            for a_, b_, c_ in hit:
                st.markdown(f"**{a_}** — {b_}" + (f"  \n💡 {c_}" if c_ else ""))
    if kw and shown == 0:
        st.info("검색 결과가 없습니다. 다른 단어로 찾아보세요.")
