#!/usr/bin/env python3
"""
Crypto Morning News Scraper + Scorer
- Fetch from multiple sources
- Score each article (0-10) using rule-based + LLM
- Only keep >= 8.0
- Save raw data locally
- Send top items to Telegram
"""

import os, json, re, time, hashlib, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import feedparser
import requests
import pandas as pd

# ========== CONFIG ==========
CONFIG = {
    # Thresholds
    "MIN_SCORE": 8.0,
    "LOOKBACK_HOURS": 18,
    "MAX_ITEMS_PER_SOURCE": 50,
    
    # Storage
    "DATA_DIR": Path.home() / "crypto_news_data",
    "DB_PATH": Path.home() / "crypto_news_data" / "news.db",
    "RAW_DIR": Path.home() / "crypto_news_data" / "raw",
    
    # Telegram
    "TG_BOT_TOKEN": os.getenv("TG_BOT_TOKEN"),
    "TG_CHAT_ID": os.getenv("TG_CHAT_ID"),
    
    # LLM (OpenRouter)
    "LLM_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    "LLM_MODEL": "nvidia/nemotron-3-ultra-550b-a55b:free",
    "LLM_BASE_URL": "https://openrouter.ai/api/v1/chat/completions",
    
    # Sources
    "SOURCES": {
        "coindesk": {
            "type": "rss",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "credibility": 0.95,
            "tags": ["general", "regulation", "institutional"]
        },
        "theblock": {
            "type": "rss",
            "url": "https://www.theblock.co/rss.xml",
            "credibility": 0.98,
            "tags": ["research", "onchain", "defi", "institutional"]
        },
        "cointelegraph": {
            "type": "rss",
            "url": "https://cointelegraph.com/rss",
            "credibility": 0.85,
            "tags": ["general", "altcoins", "nft", "gaming"]
        },
        "decrypt": {
            "type": "rss",
            "url": "https://decrypt.co/feed",
            "credibility": 0.88,
            "tags": ["defi", "eth", "web3", "policy"]
        },
        "bitcoinmagazine": {
            "type": "rss",
            "url": "https://bitcoinmagazine.com/.rss/full/",
            "credibility": 0.90,
            "tags": ["btc", "lightning", "mining", "macro"]
        },
        "bankless": {
            "type": "rss",
            "url": "https://bankless.substack.com/feed",
            "credibility": 0.92,
            "tags": ["eth", "defi", "rollups", "eigenlayer"]
        },
        "cryptopanic": {
            "type": "json",
            "url": "https://cryptopanic.com/api/free/v1/posts/?auth_token={CRYPTOPANIC_TOKEN}&public=true&filter=hot",
            "credibility": 0.80,
            "tags": ["aggregator", "sentiment", "breaking"]
        },
        "coingecko_trending": {
            "type": "json",
            "url": "https://api.coingecko.com/api/v3/search/trending",
            "credibility": 0.75,
            "tags": ["trending", "price_action", "new_listings"]
        },
        "fear_greed": {
            "type": "json",
            "url": "https://api.alternative.me/fng/?limit=1",
            "credibility": 0.70,
            "tags": ["sentiment", "market_psychology"]
        }
    },
    
    # Scoring weights
    "WEIGHTS": {
        "source_credibility": 0.15,
        "keyword_match": 0.40,
        "recency": 0.10,
        "title_quality": 0.05,
        "llm_score": 0.30
    }
}

# ========== KEYWORDS & PATTERNS ==========
HIGH_IMPACT_KEYWORDS = {
    # Tier 1: Maximum impact (weight 3.0)
    "etf approval": 3.0, "etf launch": 3.0, "sec approval": 3.0, "sec lawsuit": 3.0,
    "hack": 3.0, "exploit": 3.0, "drain": 3.0, "rug pull": 3.0, "vulnerability": 3.0,
    "bounty": 2.5, "stolen": 2.5, "compromised": 2.5, "breach": 2.5,
    "mainnet launch": 2.5, "token launch": 2.3, "airdrop": 2.2, "tge": 2.2,
    "upgrade": 2.0, "hard fork": 2.0, "proposal passed": 2.0, "governance attack": 2.5,
    "whale": 2.0, "large transfer": 1.8, "dormant wallet": 1.8, "accumulation": 1.8,
    "institutional adoption": 2.2, "treasury": 2.0, "etf flow": 2.2,
    "regulation": 2.0, "bill passed": 2.2, "executive order": 2.2,
    "partnership": 1.6, "integration": 1.4, "listing": 1.8, "delisting": 2.0,
    "bankruptcy": 2.5, "liquidation": 2.0, "insolvency": 2.3,
    "stablecoin depeg": 2.8, "depeg": 2.5, "redemption": 1.8,
    "bridging": 1.4, "bridge hack": 3.0, "cross-chain": 1.4,
}

MEDIUM_KEYWORDS = {
    "roadmap": 1.0, "testnet": 1.0, "devnet": 0.9, "whitepaper": 0.9,
    "hiring": 0.7, "grant": 0.9, "funding": 1.0, "raise": 1.1,
    "partnership": 1.0, "collaboration": 0.9, "ecosystem": 0.9,
    "yield": 1.0, "apy": 0.9, "staking": 1.0, "restaking": 1.1,
    "layer2": 1.0, "l2": 1.0, "rollup": 1.0, "validium": 0.9,
    "zk": 1.0, "zero-knowledge": 1.0, "proof": 0.9,
    "memecoin": 0.9, "ai agent": 1.0, "depin": 1.0, "rwa": 1.1,
    "inflow": 1.5, "outflow": 1.5, "inflows": 1.5, "outflows": 1.5,
    "surge": 1.3, "jump": 1.3, "rally": 1.3, "pump": 1.2,
    "crash": 1.5, "dump": 1.2, "drop": 1.0, "slip": 0.8,
    "record": 1.2, "all-time high": 1.5, "ath": 1.5,
    "approval": 1.5, "approved": 1.5, "license": 1.3, "licensed": 1.3,
    "acquisition": 1.5, "merger": 1.4, "investment": 1.2,
}

NEGATIVE_KEYWORDS = {
    "opinion": -0.5, "analysis": -0.3, "prediction": -0.3, "price prediction": -0.5,
    "technical analysis": -0.4, "ta:": -0.5, "chart": -0.3, "support": -0.2,
    "resistance": -0.2, "moon": -0.3, "pump": -0.2, "dump": -0.2,
    "shilling": -0.5, "sponsored": -0.6, "advertorial": -0.8,
    "weekly recap": -0.3, "daily recap": -0.3, "roundup": -0.4,
}

CORE_ASSETS = {"btc", "bitcoin", "eth", "ethereum", "sol", "solana", "usdt", "usdc", "dai", "bnb", "arb", "op", "matic", "pol", "apt", "sui", "inj", "tia", "celestia", "ethena", "pendle", "eigenlayer", "layerzero", "wormhole", "uniswap", "aave", "maker", "lido", "rocketpool"}

# ========== DATABASE ==========
def init_db():
    Path(CONFIG["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(CONFIG["RAW_DIR"]).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(CONFIG["DB_PATH"])
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            summary TEXT,
            url TEXT UNIQUE,
            published_at TEXT,
            fetched_at TEXT,
            raw_score REAL,
            keyword_score REAL,
            recency_score REAL,
            title_score REAL,
            llm_score REAL,
            final_score REAL,
            tags TEXT,
            kept INTEGER DEFAULT 0,
            sent_telegram INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_score ON articles(final_score)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kept ON articles(kept)")
    conn.commit()
    return conn

def article_exists(conn, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    return cur.fetchone() is not None

def save_article(conn, article: Dict):
    conn.execute("""
        INSERT OR REPLACE INTO articles 
        (id, source, title, summary, url, published_at, fetched_at,
         raw_score, keyword_score, recency_score, title_score, llm_score, final_score, tags, kept)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        article["id"], article["source"], article["title"], article["summary"],
        article["url"], article["published_at"], article["fetched_at"],
        article.get("raw_score"), article.get("keyword_score"), article.get("recency_score"),
        article.get("title_score"), article.get("llm_score"), article["final_score"],
        json.dumps(article.get("tags", [])), 1 if article["final_score"] >= CONFIG["MIN_SCORE"] else 0
    ))
    conn.commit()

# ========== FETCHERS ==========
def fetch_rss(source_name: str, cfg: Dict) -> List[Dict]:
    try:
        feed = feedparser.parse(cfg["url"])
        items = []
        for entry in feed.entries[:CONFIG["MAX_ITEMS_PER_SOURCE"]]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            dt = datetime(*pub[:6], tzinfo=timezone.utc) if pub else datetime.now(timezone.utc)
            
            if dt < datetime.now(timezone.utc) - timedelta(hours=CONFIG["LOOKBACK_HOURS"]):
                continue
            
            items.append({
                "source": source_name,
                "title": entry.get("title", "").strip(),
                "summary": (entry.get("summary") or entry.get("description") or "").strip(),
                "url": entry.get("link", "").strip(),
                "published_at": dt.isoformat(),
                "tags": cfg.get("tags", [])
            })
        return items
    except Exception as e:
        print(f"[ERROR] RSS {source_name}: {e}")
        return []

def fetch_json(source_name: str, cfg: Dict) -> List[Dict]:
    try:
        url = cfg["url"]
        if "{CRYPTOPANIC_TOKEN}" in url:
            token = os.getenv("CRYPTOPANIC_TOKEN", "")
            if not token:
                print(f"[WARN] {source_name}: No CRYPTOPANIC_TOKEN env var")
                return []
            url = url.format(CRYPTOPANIC_TOKEN=token)
        
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=CONFIG["LOOKBACK_HOURS"])
        
        if source_name == "cryptopanic":
            for post in data.get("results", [])[:CONFIG["MAX_ITEMS_PER_SOURCE"]]:
                dt = datetime.fromisoformat(post.get("created_at", "").replace("Z", "+00:00"))
                if dt < cutoff: continue
                items.append({
                    "source": source_name,
                    "title": post.get("title", "").strip(),
                    "summary": post.get("description", "")[:500].strip(),
                    "url": post.get("url", "").strip(),
                    "published_at": dt.isoformat(),
                    "tags": cfg.get("tags", []) + post.get("currencies", [])
                })
        
        elif source_name == "coingecko_trending":
            for coin in data.get("coins", [])[:10]:
                item = coin.get("item", {})
                items.append({
                    "source": source_name,
                    "title": f"Trending: {item.get('name', '')} ({item.get('symbol', '').upper()})",
                    "summary": f"Rank #{item.get('market_cap_rank', '?')}, Score: {item.get('score', 0):.1f}",
                    "url": f"https://www.coingecko.com/en/coins/{item.get('id', '')}",
                    "published_at": now.isoformat(),
                    "tags": cfg.get("tags", []) + [item.get("symbol", "").upper()]
                })
        
        elif source_name == "fear_greed":
            fng = data.get("data", [{}])[0]
            items.append({
                "source": source_name,
                "title": f"Fear & Greed Index: {fng.get('value_classification', '')} ({fng.get('value', '?')})",
                "summary": f"Market sentiment indicator. Value: {fng.get('value')}/100. {fng.get('value_classification', '')}.",
                "url": "https://alternative.me/crypto/fear-and-greed-index/",
                "published_at": now.isoformat(),
                "tags": cfg.get("tags", [])
            })
        
        return items
    except Exception as e:
        print(f"[ERROR] JSON {source_name}: {e}")
        return []

def fetch_all() -> List[Dict]:
    all_items = []
    for name, cfg in CONFIG["SOURCES"].items():
        print(f"[FETCH] {name}...")
        if cfg["type"] == "rss":
            items = fetch_rss(name, cfg)
        elif cfg["type"] == "json":
            items = fetch_json(name, cfg)
        else:
            continue
        print(f"  -> {len(items)} items")
        all_items.extend(items)
    return all_items

# ========== SCORING ==========
def compute_keyword_score(text: str) -> float:
    text_lower = text.lower()
    score = 0.0
    matched = []
    
    for kw, weight in HIGH_IMPACT_KEYWORDS.items():
        if kw in text_lower:
            score += weight
            matched.append(kw)
    
    for kw, weight in MEDIUM_KEYWORDS.items():
        if kw in text_lower:
            score += weight  # full weight now (pre-scaled)
            matched.append(kw)
    
    for kw, weight in NEGATIVE_KEYWORDS.items():
        if kw in text_lower:
            score += weight  # negative
            matched.append(kw)
    
    # Core asset bonus
    for asset in CORE_ASSETS:
        if asset in text_lower:
            score += 0.2
    
    # Cap at 10
    return min(max(score, 0), 10), matched

def compute_recency_score(published_at: str) -> float:
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if hours_ago <= 1: return 10.0
        elif hours_ago <= 3: return 9.0
        elif hours_ago <= 6: return 8.0
        elif hours_ago <= 12: return 6.5
        elif hours_ago <= 24: return 5.0
        else: return 3.0
    except:
        return 5.0

def compute_title_score(title: str) -> float:
    score = 5.0
    title_lower = title.lower()
    
    # Length penalty/bonus
    if 30 <= len(title) <= 100: score += 1.0
    elif len(title) > 140: score -= 1.0
    elif len(title) < 20: score -= 0.5
    
    # Specificity markers
    if any(c.isdigit() for c in title): score += 0.5  # numbers = specific
    if "$" in title or "₿" in title: score += 0.5
    if any(w in title_lower for w in ["breaking", "just in", "alert", "urgent"]): score += 1.0
    if "?" in title: score -= 0.5  # questions often speculative
    
    return min(max(score, 0), 10)

def llm_score_batch(articles: List[Dict], batch_size: int = 10) -> List[float]:
    """Score multiple articles in batches - fallback to rule-based if LLM fails"""
    if not articles:
        return []
    
    if not CONFIG["LLM_API_KEY"]:
        print("[WARN] No LLM API key, using heuristic score")
        return [5.0] * len(articles)
    
    all_scores = []
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        print(f"  [LLM] Scoring batch {i//batch_size + 1}/{(len(articles)-1)//batch_size + 1} ({len(batch)} items)")
        
        # Ultra-short prompt with strong constraints
        prompt = "Score 0-10. Output ONLY JSON array [n,n,...]. No text.\n\n"
        for j, a in enumerate(batch, 1):
            prompt += f"{j}. {a['title'][:80]}\n"
        
        headers = {
            "Authorization": f"Bearer {CONFIG['LLM_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": CONFIG["LLM_MODEL"],
            "messages": [
                {"role": "system", "content": "JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 100
        }
        
        try:
            resp = requests.post(CONFIG["LLM_BASE_URL"], headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            first_bracket = content.find('[')
            last_bracket = content.rfind(']')
            if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
                json_str = content[first_bracket:last_bracket+1]
                scores = json.loads(json_str)
                scores = [float(s) for s in scores if isinstance(s, (int, float))]
                if len(scores) == len(batch):
                    all_scores.extend(scores)
                    time.sleep(0.3)
                    continue
        except Exception as e:
            pass
        
        # Fallback: use keyword-based score for this batch
        print(f"  [LLM] Failed, using keyword fallback for batch")
        for a in batch:
            text = a["title"] + " " + a["summary"]
            kw_score, _ = compute_keyword_score(text)
            all_scores.append(kw_score)
        time.sleep(0.3)
    
    return all_scores

def score_article(article: Dict, keyword_score: float, kw_matched: List, llm_score: float) -> Dict:
    source_cred = CONFIG["SOURCES"].get(article["source"], {}).get("credibility", 0.7) * 10
    recency = compute_recency_score(article["published_at"])
    title_sc = compute_title_score(article["title"])
    
    w = CONFIG["WEIGHTS"]
    final = (
        w["source_credibility"] * source_cred +
        w["keyword_match"] * keyword_score +
        w["recency"] * recency +
        w["title_quality"] * title_sc +
        w["llm_score"] * llm_score
    )
    
    article.update({
        "id": hashlib.md5(article["url"].encode()).hexdigest()[:16],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw_score": round(final, 2),
        "keyword_score": round(keyword_score, 2),
        "recency_score": round(recency, 2),
        "title_score": round(title_sc, 2),
        "llm_score": round(llm_score, 2),
        "final_score": round(final, 2),
        "matched_keywords": kw_matched
    })
    return article

# ========== TELEGRAM ==========
def send_telegram(message: str) -> bool:
    if not CONFIG["TG_BOT_TOKEN"] or not CONFIG["TG_CHAT_ID"]:
        print("[WARN] Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{CONFIG['TG_BOT_TOKEN']}/sendMessage"
    payload = {
        "chat_id": CONFIG["TG_CHAT_ID"],
        "text": message[:4096],
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.ok
    except Exception as e:
        print(f"[ERROR] Telegram: {e}")
        return False

def format_telegram_message(articles: List[Dict]) -> str:
    if not articles:
        return "🌅 *Crypto Morning Brief*\n\nKhông có bài nào đạt ngưỡng ≥ 8.0 hôm nay."
    
    # Group by score tier
    tiers = {"🔥 9.5-10": [], "⚡ 9.0-9.5": [], "🎯 8.5-9.0": [], "✅ 8.0-8.5": []}
    for a in articles:
        s = a["final_score"]
        if s >= 9.5: tiers["🔥 9.5-10"].append(a)
        elif s >= 9.0: tiers["⚡ 9.0-9.5"].append(a)
        elif s >= 8.5: tiers["🎯 8.5-9.0"].append(a)
        else: tiers["✅ 8.0-8.5"].append(a)
    
    msg = f"🌅 *Crypto Morning Brief* — {datetime.now().strftime('%d/%m %H:%M')}\n"
    msg += f"📊 *{len(articles)} bài ≥ 8.0 / {sum(len(v) for v in tiers.values())} total*\n\n"
    
    for tier_name, items in tiers.items():
        if not items: continue
        msg += f"*{tier_name}* ({len(items)})\n"
        for a in items:
            kw = ", ".join(a.get("matched_keywords", [])[:3])
            msg += f"• `{a['final_score']:.1f}` [{a['source']}] {a['title'][:80]}\n"
            if kw: msg += f"  _Keys: {kw}_\n"
            msg += f"  🔗 {a['url']}\n\n"
    
    msg += f"\n💾 Raw data: `~/crypto_news_data/`"
    return msg

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("🚀 CRYPTO NEWS SCORER STARTED")
    print("=" * 60)
    
    conn = init_db()
    
    # 1. Fetch
    print("\n[1/5] Fetching sources...")
    raw_items = fetch_all()
    print(f"   Total fetched: {len(raw_items)}")
    
    # 2. Dedupe & filter new
    print("\n[2/5] Deduplicating...")
    new_items = []
    for item in raw_items:
        if not article_exists(conn, item["url"]):
            new_items.append(item)
    print(f"   New articles: {len(new_items)}")
    
    if not new_items:
        print("   Nothing new. Exiting.")
        return
    
    # 3. Keyword scoring
    print("\n[3/5] Keyword scoring...")
    for item in new_items:
        text = item["title"] + " " + item["summary"]
        kw_score, matched = compute_keyword_score(text)
        item["_kw_score"] = kw_score
        item["_kw_matched"] = matched
    
    # 4. LLM scoring (batch)
    print("\n[4/5] LLM scoring...")
    llm_scores = llm_score_batch(new_items)
    
    # 5. Final scoring & save
    print("\n[5/5] Final scoring & saving...")
    high_score = []
    for item, llm_sc in zip(new_items, llm_scores):
        scored = score_article(item, item["_kw_score"], item["_kw_matched"], llm_sc)
        save_article(conn, scored)
        if scored["final_score"] >= CONFIG["MIN_SCORE"]:
            high_score.append(scored)
    
    # Sort high score descending
    high_score.sort(key=lambda x: x["final_score"], reverse=True)
    
    # Save raw JSON for audit
    raw_file = CONFIG["RAW_DIR"] / f"raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump([{
            "title": a["title"], "source": a["source"], "url": a["url"],
            "score": a["final_score"], "keywords": a.get("matched_keywords", [])
        } for a in high_score], f, ensure_ascii=False, indent=2)
    
    # Send Telegram
    print(f"\n📤 Sending {len(high_score)} high-score articles to Telegram...")
    msg = format_telegram_message(high_score)
    send_telegram(msg)
    
    # Update sent flag
    for a in high_score:
        conn.execute("UPDATE articles SET sent_telegram = 1 WHERE id = ?", (a["id"],))
    conn.commit()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ DONE — {len(high_score)} articles ≥ {CONFIG['MIN_SCORE']}")
    print(f"💾 Raw saved: {raw_file}")
    print(f"🗄️ DB: {CONFIG['DB_PATH']}")
    for a in high_score[:5]:
        print(f"  {a['final_score']:.1f} | {a['source']} | {a['title'][:60]}")
    print("=" * 60)

if __name__ == "__main__":
    main()