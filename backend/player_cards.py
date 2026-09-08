"""Read card assets from the official Data Center; never return its executable HTML."""

from collections import OrderedDict
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/player-database")
_cache = OrderedDict()
_cache_lock = Lock()
_request_locks = [Lock() for _ in range(32)]
_cache_ttl = 12 * 60 * 60
_asset_hosts = {"ssl.nexon.com", "fco.dn.nexoncdn.co.kr", "fo4.dn.nexoncdn.co.kr"}


def official_asset_url(value):
    parts = urlsplit(str(value or ""))
    if parts.scheme not in ("https", "") or parts.hostname not in _asset_hosts:
        return ""
    # The official page adds a changing rd timestamp; keep assets browser-cacheable.
    return urlunsplit(("https", parts.netloc, parts.path, "", ""))


def parse_official_card(html, sp_id):
    soup = BeautifulSoup(html, "html.parser")
    card = soup.select_one(".playerCard") or soup.select_one(".playerThumb")
    if card is None:
        raise ValueError("Official player card was not found")

    def image(selector):
        element = card.select_one(selector)
        return official_asset_url(element.get("src")) if element else ""

    def text(selector):
        element = card.select_one(selector)
        return element.get_text(" ", strip=True) if element else ""

    wrapper = card.select_one(".playerCardWrap, .playerWrap")
    season_class = next((c for c in (wrapper.get("class", []) if wrapper else [])
                         if c.startswith("_")), "")
    result = {
        "sp_id": sp_id,
        "background_url": image(".cardBack img, .back img"),
        "portrait_url": image(".playerCardThumb .img img, .thumb .img img"),
        "portrait_kind": "head" if card.select_one(".img.head") else "action",
        "season_url": image(".season img"),
        "season_class": season_class,
        "nation_url": image(".nation img"),
        "league_url": image(".league img"),
        "team_url": image(".team img"),
        "player_name": text(".name"),
        "position": text(".position"),
        "salary": text(".pay span"),
        "source": "https://fconline.nexon.com/datacenter",
    }
    if not result["background_url"] or not result["portrait_url"]:
        raise ValueError("Official card assets were not found")
    return result


def get_official_card(sp_id):
    # Coalesce requests for the same card (search, pitch, and dialog share assets).
    with _request_locks[sp_id % len(_request_locks)]:
        with _cache_lock:
            cached = _cache.get(sp_id)
            if cached and monotonic() - cached[0] < _cache_ttl:
                _cache.move_to_end(sp_id)
                return cached[1]
        response = httpx.get(
            "https://fconline.nexon.com/datacenter/PlayerAbility",
            params={"spid": sp_id, "n1Strong": 1, "n1Grow": 0, "n1Change": 0},
            headers={"Referer": "https://fconline.nexon.com/datacenter/",
                     "User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        result = parse_official_card(response.text, sp_id)
        with _cache_lock:
            _cache[sp_id] = (monotonic(), result)
            _cache.move_to_end(sp_id)
            while len(_cache) > 1024:
                _cache.popitem(last=False)
        return result


@router.get("/card/{sp_id}")
def player_card_assets(sp_id: int, response: Response):
    if not 1_000_000 <= sp_id <= 999_999_999:
        raise HTTPException(status_code=400, detail="선수 ID가 올바르지 않습니다.")
    try:
        result = get_official_card(sp_id)
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(status_code=502, detail="공식 선수 카드를 불러오지 못했습니다.") from error
    response.headers["Cache-Control"] = "public, max-age=3600"
    return result
