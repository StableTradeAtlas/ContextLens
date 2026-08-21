from __future__ import annotations

import hashlib
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Callable

from app.config import get_settings
from app.historical_maps import build_experience, historical_map_payload
from app.library_client import ShanghaiLibraryClient, canonical_source_uri
from app.models import HistoricalClaim, HistoricalFeature, PlaceCandidate


PLACE_TOKEN_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9·]{1,18}(?:中路|东路|西路|南路|北路|大道|公路|马路|路|街|弄|里|浜|桥|码头|外滩|广场))")
HOUSE_RE = re.compile(r"(\d+(?:[-—至]\d+)?(?:弄\d+)?号(?:甲|乙|丙)?)")
YEAR_RE = re.compile(r"(?<!\d)(1[6-9]\d{2}|20\d{2})(?!\d)")
MODERN_NAME_RE = re.compile(r"(?:今|现名|现为|现称)[（(]?([\u4e00-\u9fff]{2,14}(?:中路|东路|西路|南路|北路|大道|路|街|弄|里|外滩))")
GENERIC_PLACE_TERMS = {"上海", "历史", "旧址", "附近", "地址", "马路", "道路", "那里", "这里"}


def _feature(
    feature_id: str,
    feature_type: str,
    title: str,
    description: str,
    source_uri: str,
    source_title: str,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
    longitude: float | None = None,
    latitude: float | None = None,
    spatial_precision: str = "source_coordinate",
    address: str = "",
) -> HistoricalFeature:
    return HistoricalFeature(
        feature_id=feature_id,
        feature_type=feature_type,
        title=title,
        description=description,
        source_uri=source_uri,
        source_title=source_title,
        start_year=start_year,
        end_year=end_year,
        longitude=longitude,
        latitude=latitude,
        spatial_precision=spatial_precision,
        address=address,
        evidence_ids=[feature_id],
        live_api=False,
    )


FALLBACK_CANDIDATES: dict[str, list[PlaceCandidate]] = {
    "霞飞路": [
        PlaceCandidate(
            candidate_id="place-xiafei-road",
            canonical_name="霞飞路",
            display_name="霞飞路（今淮海中路一带）",
            historical_names=["霞飞路"],
            modern_names=["淮海中路"],
            valid_to=1943,
            official_uri="https://data.library.sh.cn/entity/road/vus34wj1kewtloqv",
            source_uri="https://data.library.sh.cn/entity/road/vus34wj1kewtloqv",
            confidence=0.96,
            match_reason="旧路名精确命中；历史事件资料中明确出现“霞飞路（今淮海中路）”。",
            resolution_status="resolved",
            name_periods=[
                {"name": "西江路", "from_year": 1901, "to_year": 1906, "source_uri": "https://xmwb.xinmin.cn/html/2013-09/01/content_29_3.htm"},
                {"name": "宝昌路", "from_year": 1906, "to_year": 1915, "source_uri": "https://xmwb.xinmin.cn/html/2013-09/01/content_29_3.htm"},
                {"name": "霞飞路", "from_year": 1915, "to_year": 1943, "source_uri": "https://data.library.sh.cn/entity/road/vus34wj1kewtloqv"},
                {"name": "泰山路", "from_year": 1943, "to_year": 1945, "source_uri": "https://data.library.sh.cn/entity/road/kzourann5jxemeiz"},
                {"name": "林森中路", "from_year": 1945, "to_year": 1950, "source_uri": "https://data.library.sh.cn/entity/road/611xxq4ewmzn0loo"},
                {"name": "淮海中路", "from_year": 1950, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/m5k6iust3du2ditb"},
            ],
        )
    ],
    "南京路": [
        PlaceCandidate(
            candidate_id="place-nanjing-east-road",
            canonical_name="南京东路",
            display_name="南京路 · 南京东路商业段",
            historical_names=["南京路"],
            modern_names=["南京东路"],
            official_uri="https://data.library.sh.cn/entity/road/cnqskstreka8uy5m",
            source_uri="https://data.library.sh.cn/entity/road/cnqskstreka8uy5m",
            confidence=0.91,
            match_reason="“百货公司”等商业语境更接近南京东路，仍允许切换候选。",
            resolution_status="ambiguous",
        ),
        PlaceCandidate(
            candidate_id="place-nanjing-west-road",
            canonical_name="南京西路",
            display_name="南京路 · 南京西路段",
            historical_names=["南京路"],
            modern_names=["南京西路"],
            confidence=0.72,
            match_reason="南京路存在东西分段，需要结合门牌或建筑进一步确认。",
            resolution_status="ambiguous",
        ),
    ],
    "外滩": [
        PlaceCandidate(
            candidate_id="place-bund",
            canonical_name="外滩",
            display_name="外滩 · 中山东一路沿线",
            historical_names=["外滩"],
            modern_names=["中山东一路"],
            confidence=0.94,
            match_reason="公共历史地标精确命中。",
            resolution_status="resolved",
        )
    ],
    "武康路": [
        PlaceCandidate(
            candidate_id="place-wukang-road",
            canonical_name="武康路",
            display_name="武康路历史街区",
            historical_names=["福开森路"],
            modern_names=["武康路"],
            confidence=0.96,
            match_reason="现代路名精确命中，并可关联历史建筑。",
            resolution_status="resolved",
        )
    ],
    "衡山路": [
        PlaceCandidate(
            candidate_id="place-hengshan-road",
            canonical_name="衡山路",
            display_name="衡山路 · 原贝当路",
            historical_names=["贝当路"],
            modern_names=["衡山路"],
            valid_from=1943,
            official_uri="https://data.library.sh.cn/entity/road/5usd0gq8j62kwpv8",
            source_uri="https://data.library.sh.cn/entity/road/5usd0gq8j62kwpv8",
            confidence=0.97,
            match_reason="上海图书馆道路实体记录贝当路与衡山路的旧今关联。",
            resolution_status="resolved",
            name_periods=[
                {"name": "贝当路", "from_year": None, "to_year": 1943, "source_uri": "https://data.library.sh.cn/entity/road/5zvyegqgbscjilqy"},
                {"name": "衡山路", "from_year": 1943, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/5usd0gq8j62kwpv8"},
            ],
        )
    ],
    "南京西路": [
        PlaceCandidate(
            candidate_id="place-nanjing-west-road-curated",
            canonical_name="南京西路",
            display_name="南京西路 · 原静安寺路",
            historical_names=["静安寺路"],
            modern_names=["南京西路"],
            valid_from=1945,
            official_uri="https://data.library.sh.cn/entity/road/o4djhtmu08plgpn8",
            source_uri="https://data.library.sh.cn/entity/road/o4djhtmu08plgpn8",
            confidence=0.97,
            match_reason="上海图书馆道路实体记录静安寺路与南京西路的旧今关联。",
            resolution_status="resolved",
            name_periods=[
                {"name": "静安寺路", "from_year": None, "to_year": 1945, "source_uri": "https://data.library.sh.cn/entity/road/13uq8a83nqemxi0j"},
                {"name": "南京西路", "from_year": 1945, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/o4djhtmu08plgpn8"},
            ],
        )
    ],
    "四川北路": [
        PlaceCandidate(
            candidate_id="place-sichuan-north-road",
            canonical_name="四川北路",
            display_name="四川北路 · 原北四川路",
            historical_names=["北四川路"],
            modern_names=["四川北路"],
            valid_from=1946,
            official_uri="https://data.library.sh.cn/entity/road/tog5ogoxxhb7ml3s",
            source_uri="https://data.library.sh.cn/entity/road/tog5ogoxxhb7ml3s",
            confidence=0.97,
            match_reason="上海图书馆道路实体记录北四川路于1946年关联为四川北路。",
            resolution_status="resolved",
            name_periods=[
                {"name": "北四川路", "from_year": None, "to_year": 1946, "source_uri": "https://data.library.sh.cn/entity/road/s8pyhxbkv5tq13bl"},
                {"name": "四川北路", "from_year": 1946, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/tog5ogoxxhb7ml3s"},
            ],
        )
    ],
    "福州路": [
        PlaceCandidate(
            candidate_id="place-fuzhou-road",
            canonical_name="福州路",
            display_name="福州路文化街",
            historical_names=[],
            modern_names=["福州路"],
            official_uri="https://data.library.sh.cn/entity/road/g0bguh688tiq65ge",
            source_uri="https://data.library.sh.cn/entity/road/g0bguh688tiq65ge",
            confidence=0.98,
            match_reason="上海图书馆地名志道路实体精确命中。",
            resolution_status="resolved",
        )
    ],
    "多伦路": [
        PlaceCandidate(
            candidate_id="place-duolun-road",
            canonical_name="多伦路",
            display_name="多伦路 · 原窦乐安路",
            historical_names=["窦乐安路"],
            modern_names=["多伦路"],
            valid_from=1943,
            official_uri="https://data.library.sh.cn/entity/road/l3khpru4rjursjdv",
            source_uri="https://data.library.sh.cn/entity/road/l3khpru4rjursjdv",
            confidence=0.97,
            match_reason="上海图书馆道路实体记录窦乐安路与多伦路的旧今关联。",
            resolution_status="resolved",
            name_periods=[
                {"name": "窦乐安路", "from_year": None, "to_year": 1943, "source_uri": "https://data.library.sh.cn/entity/road/cliobhmq3g0h3sxn"},
                {"name": "多伦路", "from_year": 1943, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/l3khpru4rjursjdv"},
            ],
        )
    ],
    "山阴路": [
        PlaceCandidate(
            candidate_id="place-shanyin-road",
            canonical_name="山阴路",
            display_name="山阴路 · 原施高塔路",
            historical_names=["施高塔路"],
            modern_names=["山阴路"],
            valid_from=1943,
            official_uri="https://data.library.sh.cn/entity/road/qy5apabloho448t2",
            source_uri="https://data.library.sh.cn/entity/road/qy5apabloho448t2",
            confidence=0.97,
            match_reason="上海图书馆道路实体记录施高塔路与山阴路的旧今关联。",
            resolution_status="resolved",
            name_periods=[
                {"name": "施高塔路", "from_year": None, "to_year": 1943, "source_uri": "https://data.library.sh.cn/entity/road/tkvxrqpjxpkjyzgd"},
                {"name": "山阴路", "from_year": 1943, "to_year": None, "source_uri": "https://data.library.sh.cn/entity/road/qy5apabloho448t2"},
            ],
        )
    ],
}


FALLBACK_FEATURES: dict[str, list[HistoricalFeature]] = {
    "霞飞路": [
        _feature(
            "event-kangjian-1934",
            "event",
            "康健书局创办",
            "康健书局创办于1934年，设址霞飞路（今淮海中路）436号，至1950年存在。",
            "https://data.library.sh.cn/authority/event/04jaae3kvaff22d1",
            "上海市历史文化事件知识库",
            start_year=1934,
            end_year=1950,
            longitude=121.4770,
            latitude=31.2274,
            spatial_precision="road_approximation",
            address="霞飞路436号",
        ),
        _feature(
            "building-guotai",
            "building",
            "国泰电影院",
            "上海优秀历史建筑，位于淮海中路870号。",
            "https://data.library.sh.cn/entity/architecture/5n2kx2v82uuujr6o",
            "上海优秀历史建筑",
            longitude=121.46779,
            latitude=31.224125,
            address="淮海中路870号",
        ),
        _feature(
            "event-liuhaisu-1927",
            "event",
            "刘海粟近作展览会",
            "1927年刘海粟在霞飞路尚贤堂举办近作展览会，相关报道见《时报》和《上海画报》。",
            "https://data.library.sh.cn/authority/event/2xc6cvwej1sckvg5",
            "上海市历史文化事件知识库",
            start_year=1927,
            end_year=1927,
            longitude=121.4718,
            latitude=31.2254,
            spatial_precision="road_approximation",
            address="霞飞路尚贤堂",
        ),
    ],
    "南京东路": [
        _feature(
            "building-first-department-store",
            "building",
            "上海市第一百货商店",
            "上海优秀历史建筑记录，位于南京东路330号。",
            "https://data.library.sh.cn/entity/architecture/71lebilu80bbmb5n",
            "上海优秀历史建筑",
            longitude=121.49024,
            latitude=31.243027,
            address="南京东路330号",
        ),
        _feature(
            "building-first-food-store",
            "building",
            "上海第一食品商店",
            "上海优秀历史建筑记录，位于南京东路720号。",
            "https://data.library.sh.cn/entity/architecture/tu2qdkt5qq1z0bj5",
            "上海优秀历史建筑",
            longitude=121.483315,
            latitude=31.24128,
            address="南京东路720号",
        ),
    ],
    "外滩": [
        _feature(
            "building-peace-hotel",
            "building",
            "和平饭店北楼",
            "北楼建于1929年，原名华懋饭店，位于中山东一路20号。",
            "https://data.library.sh.cn/entity/architecture/2iloklca2gojo53e",
            "上海优秀历史建筑",
            start_year=1929,
            longitude=121.49633,
            latitude=31.244972,
            address="中山东一路20号",
        ),
        _feature(
            "building-bund-observatory",
            "building",
            "外滩天文台",
            "外滩历史陈列室与外滩天文台，位于中山东二路1号甲。",
            "https://data.library.sh.cn/entity/architecture/7cy7p8b8w6ufxvbe",
            "上海优秀历史建筑",
            longitude=121.49901,
            latitude=31.238583,
            address="中山东二路1号甲",
        ),
    ],
    "武康路": [
        _feature(
            "building-wukang-129",
            "building",
            "德利那齐宅",
            "上海优秀历史建筑记录，位于武康路129号。",
            "https://data.library.sh.cn/entity/architecture/45ob5f3b5swdj5yc",
            "上海优秀历史建筑",
            longitude=121.446365,
            latitude=31.213299,
            address="武康路129号",
        ),
        _feature(
            "building-wukang-210",
            "building",
            "武康路210号住宅",
            "上海优秀历史建筑记录中的武康路住宅。",
            "https://data.library.sh.cn/entity/architecture/5cga1cuxin4rph8d",
            "上海优秀历史建筑",
            longitude=121.4469,
            latitude=31.215696,
            address="武康路210号",
        ),
    ],
    "衡山路": [
        _feature(
            "building-georgia-apartments",
            "building",
            "集雅公寓",
            "上海优秀历史建筑数据记录其位于衡山路311—331号，又名乔治公寓。",
            "https://data.library.sh.cn/entity/architecture/2tp3c0ieswi51fnc",
            "上海优秀历史建筑",
            longitude=121.451355,
            latitude=31.208702,
            address="衡山路311—331号",
        ),
        _feature(
            "building-community-church",
            "building",
            "国际礼拜堂",
            "上海优秀历史建筑数据记录其位于衡山路一带，并记载1925年建成。",
            "https://data.library.sh.cn/entity/architecture/fnnc0iu27xtxua75",
            "上海优秀历史建筑",
            start_year=1925,
            longitude=121.45236,
            latitude=31.210646,
            address="衡山路58号（来源文本存在53/58号差异，门牌待复核）",
            spatial_precision="source_coordinate",
        ),
    ],
    "南京西路": [
        _feature(
            "building-jingan-villas",
            "building",
            "静安别墅",
            "上海优秀历史建筑数据记载静安别墅位于南京西路1025弄，1932年建成，并明确提及静安寺路（今南京西路）。",
            "https://data.library.sh.cn/entity/architecture/ntzw3megdqvc3r65",
            "上海优秀历史建筑",
            start_year=1932,
            longitude=121.46551,
            latitude=31.23331,
            address="南京西路1025弄",
        ),
        _feature(
            "building-park-hotel",
            "building",
            "国际饭店",
            "上海优秀历史建筑数据记录国际饭店位于南京西路170号。",
            "https://data.library.sh.cn/entity/architecture/hyjs2zl66id4qicl",
            "上海优秀历史建筑",
            longitude=121.47829,
            latitude=31.239466,
            address="南京西路170号",
        ),
    ],
    "四川北路": [
        _feature(
            "building-bridge-apartments",
            "building",
            "大桥大楼",
            "上海优秀历史建筑数据记载大桥大楼原名大桥公寓，1935年初建。",
            "https://data.library.sh.cn/entity/architecture/7irjv3wsl6ls0ak8",
            "上海优秀历史建筑",
            start_year=1935,
            longitude=121.49171,
            latitude=31.251913,
            address="四川北路85号",
        ),
        _feature(
            "building-beichuan-apartments",
            "building",
            "北川公寓",
            "上海优秀历史建筑记录中的四川北路公寓。",
            "https://data.library.sh.cn/entity/architecture/4plwh24avz4v6viq",
            "上海优秀历史建筑",
            longitude=121.489235,
            latitude=31.270388,
            address="四川北路2079—2099号",
        ),
    ],
    "福州路": [
        _feature(
            "building-foreign-language-bookstore",
            "building",
            "外文书店",
            "上海优秀历史建筑数据记录外文书店位于福州路390号；未从该记录推断创建年份。",
            "https://data.library.sh.cn/entity/architecture/6zae7d1mpck7im1u",
            "上海优秀历史建筑",
            longitude=121.48955,
            latitude=31.23987,
            address="福州路390号",
        ),
        _feature(
            "building-fuzhou-379",
            "building",
            "福州路379弄50号",
            "上海优秀历史建筑数据中的福州路建筑记录。",
            "https://data.library.sh.cn/entity/architecture/sqjcug2vkpthnqfq",
            "上海优秀历史建筑",
            longitude=121.489876,
            latitude=31.238945,
            address="福州路379弄50号",
        ),
    ],
    "多伦路": [
        _feature(
            "building-hongde-church",
            "building",
            "鸿德堂",
            "上海优秀历史建筑数据记载鸿德堂始建于1925年、1928年落成。",
            "https://data.library.sh.cn/entity/architecture/hftnzhlqq0is5kbr",
            "上海优秀历史建筑",
            start_year=1925,
            longitude=121.48906,
            latitude=31.267815,
            address="多伦路59号",
        ),
        _feature(
            "building-yongan-li",
            "building",
            "永安里",
            "上海优秀历史建筑数据记录永安里跨四川北路与多伦路。",
            "https://data.library.sh.cn/entity/architecture/g2ojoo45yk34jidd",
            "上海优秀历史建筑",
            longitude=121.488434,
            latitude=31.268679,
            address="四川北路1953弄、多伦路152—192号",
        ),
    ],
    "山阴路": [
        _feature(
            "building-hengfeng-li",
            "building",
            "恒丰里",
            "上海优秀历史建筑数据记录中的山阴路里弄；描述为较大规模石库门住区。",
            "https://data.library.sh.cn/entity/architecture/t0u68i08edvtzs4f",
            "上海优秀历史建筑",
            longitude=121.492744,
            latitude=31.271088,
            address="山阴路85弄",
        ),
        _feature(
            "building-jishan-li",
            "building",
            "积善里",
            "上海优秀历史建筑数据中的山阴路里弄记录。",
            "https://data.library.sh.cn/entity/architecture/61ojlboset3kecy7",
            "上海优秀历史建筑",
            longitude=121.49161,
            latitude=31.275036,
            address="山阴路340弄",
        ),
    ],
}


# Second curated city ring. Every road identity and every building below was
# checked against the Shanghai Library road or architecture endpoint. This is
# deliberately metadata-first: missing construction years remain ``None``.
_EXPANDED_ROADS = [
    ("瑞金二路", "瑞金二路 · 曾名中正南二路", "中正南二路", "https://data.library.sh.cn/entity/road/tm3hldwj5gjv0xsr", "https://data.library.sh.cn/entity/road/nofs35qb7vfjlt57", 1950, 1945),
    ("重庆南路", "重庆南路 · 曾名灵宝路", "灵宝路", "https://data.library.sh.cn/entity/road/cwd31q0kv2lj83mr", "https://data.library.sh.cn/entity/road/6sfswky0qexlmmq2", 1946, 1943),
    ("陕西南路", "陕西南路 · 曾名咸阳路", "咸阳路", "https://data.library.sh.cn/entity/road/aufj5pn27d13es83", "https://data.library.sh.cn/entity/road/mk7wk2u8y2y4chx8", 1946, 1943),
    ("华山路", "华山路 · 原海格路", "海格路", "https://data.library.sh.cn/entity/road/dbg5p115zojjx0sa", "https://data.library.sh.cn/entity/road/xvd0qbiyu13vsxim", 1943, None),
    ("安福路", "安福路 · 原巨泼来斯路", "巨泼来斯路", "https://data.library.sh.cn/entity/road/74qpvcvc4evlh0h2", "https://data.library.sh.cn/entity/road/opi5mvme8skhsojv", 1943, None),
    ("复兴西路", "复兴西路 · 曾名西大兴路", "西大兴路", "https://data.library.sh.cn/entity/road/b7wxeong38y7z6ex", "https://data.library.sh.cn/entity/road/75uhi3t4vjda65b0", 1945, 1943),
    ("巨鹿路", "巨鹿路 · 原巨籁达路", "巨籁达路", "https://data.library.sh.cn/entity/road/ohmgpdk2he5wxrol", "https://data.library.sh.cn/entity/road/dfnldtt1jcplqld7", 1943, None),
    ("常熟路", "常熟路 · 原善钟路", "善钟路", "https://data.library.sh.cn/entity/road/mz8gae2ptj6fi251", "https://data.library.sh.cn/entity/road/yo0bpc6rbslkzh1k", 1943, None),
    ("新乐路", "新乐路 · 原亨利路", "亨利路", "https://data.library.sh.cn/entity/road/g56o3oqb3xf4l2uz", "https://data.library.sh.cn/entity/road/s5xh8rmxr6uu6vy5", 1943, None),
    ("黄陂南路", "黄陂南路 · 曾名南黄陂路", "南黄陂路", "https://data.library.sh.cn/entity/road/xwtbcbcp50nv8krb", "https://data.library.sh.cn/entity/road/yjf8casdmg8esjg8", 1946, 1943),
    ("长阳路", "长阳路 · 原华德路", "华德路", "https://data.library.sh.cn/entity/road/ncst8y0y6mn1t57t", "https://data.library.sh.cn/entity/road/6pvnxbwszmvzu0su", 1943, None),
    ("延安中路", "延安中路 · 原中正中路", "中正中路", "https://data.library.sh.cn/entity/road/4rnh64e07b70iunt", "https://data.library.sh.cn/entity/road/kc573wnzuk4ucftv", 1950, None),
]

for _name, _display, _old_name, _old_uri, _modern_uri, _change_year, _old_from in _EXPANDED_ROADS:
    FALLBACK_CANDIDATES[_name] = [
        PlaceCandidate(
            candidate_id=f"place-expanded-{hashlib.sha1(_modern_uri.encode('utf-8')).hexdigest()[:12]}",
            canonical_name=_name,
            display_name=_display,
            historical_names=[_old_name],
            modern_names=[_name],
            valid_from=_change_year,
            official_uri=_modern_uri,
            source_uri=_modern_uri,
            confidence=0.97,
            match_reason=f"上海图书馆道路实体记录{_old_name}与{_name}的历史关联。",
            resolution_status="resolved",
            name_periods=[
                {"name": _old_name, "from_year": _old_from, "to_year": _change_year, "source_uri": _old_uri},
                {"name": _name, "from_year": _change_year, "to_year": None, "source_uri": _modern_uri},
            ],
        )
    ]


_EXPANDED_BUILDINGS = [
    ("瑞金二路", "ruijin-hospital-8", "瑞金医院8号楼", "上海优秀历史建筑数据中的瑞金二路建筑记录。", "e0tsspn8k1lo41nu", 121.4726, 31.217703, "瑞金二路197号", None),
    ("瑞金二路", "ruijin-residence", "瑞金二路沿线住宅", "来源记录跨绍兴路与瑞金二路，地图仅显示来源坐标。", "2h56b8o3ew72d88p", 121.47272, 31.215538, "瑞金二路146、148、158号", None),
    ("重庆南路", "chongqing-apartment", "重庆公寓", "来源记载建筑旧称吕班公寓，1931年建成。", "zwa45qyynjq40yth", 121.47758, 31.221407, "重庆南路185号", 1931),
    ("重庆南路", "luwan-office", "原卢湾区政府2号楼", "上海优秀历史建筑数据中的重庆南路建筑记录。", "bgvnvku5kvedrp77", 121.47879, 31.225891, "重庆南路139号", None),
    ("陕西南路", "yaerpei-lane", "亚尔培坊", "来源描述明确记载该新式里弄位于今陕西南路582弄，建于1920年。", "4qdh3v8nebcri481", 121.45153, 31.209314, "陕西南路582弄（来源坐标需结合跨路段描述复核）", 1920),
    ("华山路", "dingxiang-villa", "丁香别墅", "来源记载丁香别墅位于华山路922号，建于20世纪30年代前后。", "gii5mgilccxk4oi8", 121.444786, 31.218775, "华山路922号", None),
    ("华山路", "brookside-apartment", "枕流公寓", "来源记载枕流公寓于1930年翻建。", "ulupnnew0ta6jpri", 121.44627, 31.22201, "华山路699—731号", 1930),
    ("安福路", "anfuroad-255", "安福路255号住宅", "上海优秀历史建筑数据中的安福路住宅记录。", "5611olinjytmpobx", 121.448074, 31.219845, "安福路255号", None),
    ("安福路", "people-art-theatre", "上海人民艺术剧院旧址记录", "上海优秀历史建筑数据中的安福路建筑记录。", "6r5516zaqvy6zggs", 121.448265, 31.22001, "安福路284号", None),
    ("复兴西路", "fuxingwest-299", "复兴西路299弄住宅", "上海优秀历史建筑数据中的复兴西路住宅记录。", "chzfqp72dkix810n", 121.444695, 31.217186, "复兴西路299弄1号", None),
    ("复兴西路", "fuxingwest-147", "复兴西路147号住宅", "上海优秀历史建筑数据中的复兴西路住宅记录。", "5df1o5mdn655gkhq", 121.44874, 31.216974, "复兴西路147号", None),
    ("巨鹿路", "julu-889", "巨鹿路889号建筑", "上海优秀历史建筑数据中的巨鹿路建筑记录。", "axw6dfdlsjtlebaz", 121.45481, 31.224728, "巨鹿路889号", None),
    ("巨鹿路", "writers-association", "上海市作家协会所在建筑", "上海优秀历史建筑数据中的巨鹿路建筑记录。", "5dq3rbukzh2wwjle", 121.46282, 31.227753, "巨鹿路675—681号", None),
    ("常熟路", "rongkang-villas", "荣康别墅", "来源记载荣康别墅建于1939年。", "jn22i8hrjaycilht", 121.4542, 31.223051, "常熟路102—120号", 1939),
    ("常熟路", "ruihua-apartment", "瑞华公寓", "上海优秀历史建筑数据中的常熟路公寓记录。", "8h4eh0vbyf7hrfyn", 121.455666, 31.220133, "常熟路209号", None),
    ("新乐路", "orthodox-church", "东正教堂", "上海优秀历史建筑数据中的新乐路建筑记录。", "c0e1tftqyvqttife", 121.46205, 31.223507, "新乐路55号", None),
    ("新乐路", "xinle-44", "新乐路44号住宅", "上海优秀历史建筑数据中的新乐路住宅记录。", "4adpt5ptgu8ck88t", 121.46336, 31.224382, "新乐路44号", None),
    ("黄陂南路", "meilan-lane", "梅兰坊", "上海优秀历史建筑数据中的黄陂南路里弄记录。", "fegay1vjketra4p8", 121.483185, 31.221684, "黄陂南路596弄1—57号", None),
    ("黄陂南路", "chuneng-school", "储能中学分部建筑", "上海优秀历史建筑数据中的黄陂南路建筑记录。", "jkometc3ho70zhsi", 121.48033, 31.230295, "黄陂南路25号乙", None),
    ("长阳路", "tilanqiao-prison", "提篮桥监狱", "上海优秀历史建筑数据中的长阳路建筑记录。", "a7jx3tay3qdalrnj", 121.5167, 31.261168, "长阳路147号", None),
    ("长阳路", "ohel-moishe", "摩西会堂", "来源记载摩西会堂1927年迁至长阳路（原华德路）62号。", "ra83gxofqkz0e6y3", 121.515755, 31.259998, "长阳路62号", 1927),
    ("延安中路", "siming-lane", "四明里", "上海优秀历史建筑数据中的延安中路里弄记录。", "0dhdx80uz28zm41n", 121.4601, 31.22799, "延安中路913弄", None),
]

for _road, _feature_id, _title, _description, _architecture_id, _lon, _lat, _address, _start_year in _EXPANDED_BUILDINGS:
    FALLBACK_FEATURES.setdefault(_road, []).append(
        _feature(
            f"building-{_feature_id}",
            "building",
            _title,
            _description,
            f"https://data.library.sh.cn/entity/architecture/{_architecture_id}",
            "上海优秀历史建筑",
            start_year=_start_year,
            longitude=_lon,
            latitude=_lat,
            address=_address,
            spatial_precision="source_coordinate" if "复核" not in _address else "source_coordinate_review",
        )
    )


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def parse_public_address(address: str) -> dict[str, str]:
    cleaned = re.sub(r"[，,。；;!?！？]", " ", str(address or "").strip())[:180]
    place_match = PLACE_TOKEN_RE.search(cleaned)
    house_match = HOUSE_RE.search(cleaned)
    place = place_match.group(1) if place_match else ""
    if not place:
        for known in FALLBACK_CANDIDATES:
            if known in cleaned:
                place = known
                break
    return {
        "raw": cleaned,
        "place_term": place,
        "house_number": house_match.group(1) if house_match else "",
    }


def parse_era_hint(value: Any) -> int | None:
    match = YEAR_RE.search(str(value or ""))
    if not match:
        return None
    year = int(match.group(1))
    return year if 1600 <= year <= datetime.now().year else None


def resolve_place(address: str, era_hint: Any = None, *, allow_live: bool = True) -> dict[str, Any]:
    parsed = parse_public_address(address)
    term = parsed["place_term"]
    era = parse_era_hint(era_hint)
    if not term or term in GENERIC_PLACE_TERMS:
        return unresolved_payload(parsed, era)

    candidates: list[PlaceCandidate] = []
    live_error = ""
    settings = get_settings()
    if allow_live and settings.api_key:
        try:
            client = ShanghaiLibraryClient(settings.api_key, timeout=14)
            for item in client.search_roads(term, limit=8):
                candidate = normalize_road_candidate(item, term, parsed["house_number"], era)
                if candidate:
                    candidates.append(candidate)
        except Exception as exc:
            live_error = f"{type(exc).__name__}: {exc}"

    fallback_key = best_fallback_key(term)
    if not candidates and fallback_key:
        candidates = [PlaceCandidate(**asdict(item)) for item in FALLBACK_CANDIDATES[fallback_key]]
    elif fallback_key:
        candidates = merge_candidates(candidates, FALLBACK_CANDIDATES[fallback_key])

    if "百货" in parsed["raw"] and candidates:
        candidates.sort(key=lambda item: ("东路" in item.canonical_name, item.confidence), reverse=True)
    else:
        candidates.sort(key=lambda item: item.confidence, reverse=True)

    for item in candidates:
        item.house_number = parsed["house_number"]
    return {
        "status": "resolved" if len(candidates) == 1 else "ambiguous" if candidates else "unresolved",
        "query": {"place_term": term, "house_number": parsed["house_number"], "era_hint": era},
        "candidates": [item.to_dict() for item in candidates[:6]],
        "recommended_candidate_id": candidates[0].candidate_id if candidates else "",
        "live_api_used": any("shlib-road" in item.candidate_id for item in candidates),
        "live_error": live_error,
        "guidance": "请选择最符合记忆的地点后开始调查。" if len(candidates) > 1 else "地点身份已建立，可以进入时空调查。" if candidates else unresolved_guidance(),
    }


def unresolved_payload(parsed: dict[str, str], era: int | None) -> dict[str, Any]:
    return {
        "status": "unresolved",
        "query": {"place_term": parsed["place_term"], "house_number": parsed["house_number"], "era_hint": era},
        "candidates": [],
        "recommended_candidate_id": "",
        "live_api_used": False,
        "live_error": "",
        "guidance": unresolved_guidance(),
    }


def unresolved_guidance() -> str:
    return "暂未找到可确认的官方地点实体。请补充道路名、门牌、约略年代或附近建筑；系统不会据此编造历史。"


def best_fallback_key(term: str) -> str:
    if term in FALLBACK_CANDIDATES:
        return term
    for key, items in FALLBACK_CANDIDATES.items():
        names = [key]
        for item in items:
            names.extend(item.historical_names + item.modern_names + [item.canonical_name])
        if any(term in name or name in term for name in names):
            return key
    return ""


def normalize_road_candidate(item: dict[str, Any], term: str, house: str, era: int | None) -> PlaceCandidate | None:
    name = clean_text(item.get("nameChs") or item.get("name") or item.get("label"))
    if not name:
        return None
    uri = canonical_source_uri(clean_text(item.get("uri")))
    related_name = clean_text(item.get("historyOfName") or item.get("nameAfter"))
    valid_from, valid_to = parse_temporal_value(item.get("temporalValue"))
    exact = name == term
    confidence = 0.97 if exact else 0.83 if term in name or name in term else 0.68
    if era and valid_to and era <= valid_to:
        confidence = min(0.99, confidence + 0.02)
    return PlaceCandidate(
        candidate_id=stable_id("shlib-road", uri or name),
        canonical_name=name,
        display_name=f"{name}{f' · 关联 {related_name}' if related_name else ''}",
        historical_names=[name] if valid_to else [],
        modern_names=[related_name] if related_name else [],
        valid_from=valid_from,
        valid_to=valid_to,
        official_uri=uri,
        source_uri=uri,
        confidence=round(confidence, 2),
        match_reason="上海图书馆地名志道路实体精确命中。" if exact else "上海图书馆地名志返回相关道路候选。",
        resolution_status="resolved" if exact else "candidate",
        house_number=house,
    )


def merge_candidates(primary: list[PlaceCandidate], fallback: list[PlaceCandidate]) -> list[PlaceCandidate]:
    result = list(primary)
    known = {item.canonical_name for item in result}
    for fallback_item in fallback:
        matched = next(
            (
                item
                for item in result
                if item.canonical_name == fallback_item.canonical_name
                or fallback_item.canonical_name in item.historical_names + item.modern_names
                or item.canonical_name in fallback_item.historical_names + fallback_item.modern_names
            ),
            None,
        )
        if matched:
            matched.canonical_name = fallback_item.canonical_name
            matched.display_name = fallback_item.display_name
            matched.historical_names = unique(matched.historical_names + fallback_item.historical_names)
            # Curated aliases are ordered first so the offline flagship cases keep
            # their verified modern road name even when the live entity exposes a
            # broader ``historyOf`` relation.
            matched.modern_names = unique(fallback_item.modern_names + matched.modern_names)
            matched.name_periods = fallback_item.name_periods or matched.name_periods
            matched.official_uri = fallback_item.official_uri or matched.official_uri
            matched.source_uri = fallback_item.source_uri or matched.source_uri
            if not matched.match_reason:
                matched.match_reason = fallback_item.match_reason
        elif fallback_item.canonical_name not in known:
            result.append(PlaceCandidate(**asdict(fallback_item)))
    return result


def parse_temporal_value(value: Any) -> tuple[int | None, int | None]:
    text = clean_text(value)
    years = [int(year) for year in YEAR_RE.findall(text)]
    if not years:
        return None, None
    if text.startswith("~") or text.startswith("-"):
        return None, years[-1]
    if len(years) == 1:
        return years[0], years[0]
    return min(years), max(years)


def investigate_address(
    candidate_data: dict[str, Any],
    *,
    address: str = "",
    era_hint: Any = None,
    allow_live: bool = True,
    progress: Callable[[str, int, str], None] | None = None,
) -> dict[str, Any]:
    candidate = PlaceCandidate(**{key: value for key, value in candidate_data.items() if key in PlaceCandidate.__dataclass_fields__})
    report_progress(progress, "fetching", 30, "正在查询上图道路、事件、建筑、人物与机构资料")
    features: list[HistoricalFeature] = []
    live_errors: list[str] = []
    person_records: dict[str, list[dict[str, Any]]] = {}
    organization_records: dict[str, list[dict[str, Any]]] = {}
    settings = get_settings()
    terms = unique([candidate.canonical_name] + candidate.historical_names + candidate.modern_names)
    meaningful_terms = [term for term in terms if term and term not in GENERIC_PLACE_TERMS][:3]

    if allow_live and settings.api_key and meaningful_terms:
        client = ShanghaiLibraryClient(settings.api_key, timeout=16)
        event_term = candidate.historical_names[0] if candidate.historical_names else meaningful_terms[0]
        architecture_term = candidate.modern_names[0] if candidate.modern_names else candidate.canonical_name
        try:
            detailed_events = 0
            for item in client.search_events(event_term, limit=10):
                feature = normalize_event(item, meaningful_terms)
                if feature and detailed_events < 2 and item.get("uri"):
                    detail = client.fetch_event_detail(str(item["uri"]))
                    if detail:
                        item = {**item, **detail}
                        feature = normalize_event(item, meaningful_terms)
                    detailed_events += 1
                if feature:
                    features.append(feature)
        except Exception as exc:
            live_errors.append(f"events:{type(exc).__name__}")
        try:
            detailed_buildings = 0
            for item in client.search_architectures(architecture_term, limit=10):
                feature = normalize_architecture(item, meaningful_terms)
                if feature and detailed_buildings < 1 and item.get("uri"):
                    detail = client.fetch_architecture_detail(str(item["uri"]))
                    if detail:
                        item = {**item, **detail}
                        feature = normalize_architecture(item, meaningful_terms)
                    detailed_buildings += 1
                if feature:
                    features.append(feature)
        except Exception as exc:
            live_errors.append(f"architectures:{type(exc).__name__}")

    report_progress(progress, "linking", 62, "正在连接旧今地名、时间和空间")
    fallback_key = best_fallback_key(candidate.canonical_name)
    if not fallback_key:
        for name in candidate.historical_names + candidate.modern_names:
            fallback_key = best_fallback_key(name)
            if fallback_key:
                break
    if fallback_key:
        features = merge_features(features, FALLBACK_FEATURES.get(candidate.canonical_name, []) + FALLBACK_FEATURES.get(fallback_key, []))
    features = rank_features(features, candidate, address)

    # Person/institution expansion is deliberately selective. It only follows
    # names already present in an event/building source and never performs a
    # broad generative search. Same-name people remain explicitly ambiguous.
    if allow_live and settings.api_key:
        client = locals().get("client") or ShanghaiLibraryClient(settings.api_key, timeout=16)
        for name in unique([name for item in features for name in item.people])[:2]:
            try:
                person_records[name] = client.search_people(name, limit=4)
            except Exception as exc:
                live_errors.append(f"people:{type(exc).__name__}")
        for name in unique([name for item in features for name in item.organizations])[:1]:
            try:
                organization_records[name] = client.search_organizations(name, limit=4)
            except Exception as exc:
                live_errors.append(f"organizations:{type(exc).__name__}")

    report_progress(progress, "auditing", 82, "正在检查主张与来源")
    claims = build_place_claims(candidate, features, address=address)
    archive_network = build_archive_network(candidate, features, person_records, organization_records)
    evidence = build_evidence_cards(features, claims) + archive_network.pop("supplemental_evidence")
    era = parse_era_hint(era_hint)
    bounds = feature_bounds(features)
    resolved = bool(features)
    direct_claims = [claim for claim in claims if claim.support_level == "direct"]
    summary = build_summary(candidate, features, direct_claims)
    generated_at = datetime.now(UTC).isoformat()
    map_time = historical_map_payload(era or (features[0].start_year if features else None))
    experience = build_experience(candidate, features)
    return {
        "status": "complete",
        "candidate": candidate.to_dict(),
        "query": {
            "address_label": public_address_label(address),
            "era_hint": era,
            "focus_year": features[0].start_year if features and features[0].start_year else era,
        },
        "summary": summary,
        "finding": direct_claims[0].text if direct_claims else "暂未找到足以形成确定历史结论的直接证据。",
        "timeline": [feature_to_timeline(item) for item in sorted(features, key=feature_sort_key)],
        "feature_collection": {
            "type": "FeatureCollection",
            "features": [item.to_geojson_feature() for item in features],
        },
        "claims": [item.to_dict() for item in claims],
        "evidence": evidence,
        "archive_network": archive_network,
        "map": {
            "bounds": bounds,
            "center": feature_center(features),
            "remote_style": "https://tiles.openfreemap.org/styles/liberty",
            "historical_style": map_time["dynamic_layer"]["style_url"],
            "fallback_available": True,
            "time": map_time,
        },
        "experience": experience,
        "quality": {
            "resolved": resolved,
            "direct_claim_count": len(direct_claims),
            "source_count": len({item.source_uri for item in features if item.source_uri}),
            "archive_dataset_count": sum(1 for item in archive_network["datasets"] if item["active"]),
            "person_count": archive_network["stats"]["person_count"],
            "organization_count": archive_network["stats"]["organization_count"],
            "live_feature_count": sum(1 for item in features if item.live_api),
            "fallback_feature_count": sum(1 for item in features if not item.live_api),
            "uncertainty": "review" if any(item.spatial_precision != "source_coordinate" for item in features) else "bounded",
            "warnings": live_errors + ([] if resolved else ["no_verified_features"]),
        },
        "replay": [
            {"stage": "resolving", "label": "地址解析", "detail": f"识别地点：{candidate.display_name}"},
            {"stage": "fetching", "label": "上图多库搜索", "detail": f"检索道路、事件、建筑、人物与机构，共保留 {len(features)} 条时空特征"},
            {"stage": "linking", "label": "时空关联", "detail": "按旧今名称、年代和空间精度建立关联"},
            {"stage": "auditing", "label": "证据审计", "detail": f"形成 {len(direct_claims)} 条直接主张，其余保持背景或待考"},
        ],
        "generated_at": generated_at,
    }


def normalize_event(item: dict[str, Any], terms: list[str]) -> HistoricalFeature | None:
    title = clean_text(item.get("title") or item.get("eventTitle") or item.get("name") or item.get("label"))
    description = clean_text(item.get("description") or item.get("content") or item.get("note"))
    uri = canonical_source_uri(clean_text(item.get("uri") or item.get("eventUri")))
    text = f"{title} {description}"
    if not title or not relevant_to_place(text, terms):
        return None
    # Structured temporal fields take precedence. Address house numbers such as
    # 1708号 or 1843号 must never be misread as event years.
    years = extract_years(
        item.get("dateLabel"),
        item.get("begin"),
        item.get("end"),
        item.get("startedAtTime"),
        item.get("endedAtTime"),
    )
    if years == (None, None):
        years = extract_years(text)
    longitude = to_float(item.get("long") or item.get("longitude"))
    latitude = to_float(item.get("lat") or item.get("latitude"))
    people = relation_labels(item.get("personList"), "label", "personName")
    organizations = relation_labels(item.get("organizationList"), "label", "name")
    people = unique(people + infer_explicit_people(text))
    organizations = unique(organizations + infer_explicit_organizations(text))
    return HistoricalFeature(
        feature_id=stable_id("event", uri or title),
        feature_type="event",
        title=title,
        description=description[:900],
        source_uri=uri,
        source_title="上海市历史文化事件知识库",
        start_year=years[0],
        end_year=years[1],
        longitude=longitude,
        latitude=latitude,
        spatial_precision="source_coordinate" if longitude is not None and latitude is not None else "road_approximation",
        address=extract_address(text, terms),
        people=people,
        organizations=organizations,
        evidence_ids=[stable_id("event", uri or title)],
        live_api=True,
    )


def normalize_architecture(item: dict[str, Any], terms: list[str]) -> HistoricalFeature | None:
    title = clean_text(item.get("nameS") or item.get("nameChs") or item.get("name") or item.get("title"))
    address = clean_text(item.get("address"))
    road = clean_text(item.get("road"))
    description = clean_text(item.get("des") or item.get("description"))
    text = f"{title} {address} {road} {description}"
    if not title or not relevant_to_place(text, terms):
        return None
    uri = canonical_source_uri(clean_text(item.get("uri")))
    years = extract_years(description, item.get("created"))
    longitude = to_float(item.get("long") or item.get("longitude"))
    latitude = to_float(item.get("lat") or item.get("latitude"))
    people = relation_labels(item.get("personList"), "personName", "label", "name")
    organizations = relation_labels(item.get("organizationList"), "label", "name")
    return HistoricalFeature(
        feature_id=stable_id("building", uri or f"{title}-{address}"),
        feature_type="building",
        title=title,
        description=description[:900] or f"上海优秀历史建筑记录：{address}",
        source_uri=uri,
        source_title="上海优秀历史建筑",
        start_year=years[0],
        end_year=years[1],
        longitude=longitude,
        latitude=latitude,
        spatial_precision="source_coordinate" if longitude is not None and latitude is not None else "unknown",
        address=address,
        people=people,
        organizations=organizations,
        evidence_ids=[stable_id("building", uri or f"{title}-{address}")],
        live_api=True,
    )


def relevant_to_place(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    specific = [term for term in terms if term not in GENERIC_PLACE_TERMS and len(term) >= 2]
    return any(term.lower() in lowered for term in specific)


def relation_labels(value: Any, *keys: str) -> list[str]:
    """Read relation labels without treating arbitrary nested values as facts."""
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        if isinstance(item, dict):
            for key in keys:
                label = clean_text(item.get(key))
                if label:
                    labels.append(label)
                    break
        elif isinstance(item, str):
            labels.append(clean_text(item))
    return unique(labels)


EXPLICIT_PERSON_RE = re.compile(
    r"(?:经理|创办人|创办者|主编|校长|院长|负责人|建筑师|导演|作者)([一-鿿·]{2,4})(?=[，。；、\s]|$)"
)
PERSON_TITLE_RE = re.compile(r"^([一-鿿]{2,4})(?:近作展|画展|纪念展|诞辰|逝世|故居)")
ORGANIZATION_RE = re.compile(
    r"([一-鿿A-Za-z0-9·]{2,24}(?:书局|出版社|报馆|学校|大学|医院|公司|商店|剧院|电影院|会堂|协会|公所|银行|工厂))"
)


def infer_explicit_people(text: str) -> list[str]:
    names = [match.group(1) for match in EXPLICIT_PERSON_RE.finditer(text)]
    title_match = PERSON_TITLE_RE.search(text)
    if title_match:
        names.append(title_match.group(1))
    return unique(names)


def infer_explicit_organizations(text: str) -> list[str]:
    # Only the record title is eligible for fallback inference. Organization
    # relation lists from the official detail endpoint remain authoritative;
    # scanning full prose produced false entities such as “以后招股成立…公司”.
    title = clean_text(text).split(" ", 1)[0][:48]
    return unique([match.group(1) for match in ORGANIZATION_RE.finditer(title)])


def extract_years(*values: Any) -> tuple[int | None, int | None]:
    years: list[int] = []
    for value in values:
        years.extend(int(year) for year in YEAR_RE.findall(clean_text(value)))
    years = [year for year in years if 1600 <= year <= datetime.now().year]
    return (min(years), max(years)) if years else (None, None)


def extract_address(text: str, known_names: list[str] | None = None) -> str:
    house = HOUSE_RE.search(text)
    for name in known_names or []:
        if name and name in text:
            return f"{name}{house.group(1) if house else ''}"
    road = PLACE_TOKEN_RE.search(text)
    if not road:
        return ""
    return f"{road.group(1)}{house.group(1) if house else ''}"


def merge_features(primary: list[HistoricalFeature], fallback: list[HistoricalFeature]) -> list[HistoricalFeature]:
    result = list(primary)
    seen_uris = {item.source_uri for item in result if item.source_uri}
    seen_titles = {item.title for item in result}
    for item in fallback:
        matched = next((existing for existing in result if existing.source_uri == item.source_uri or existing.title == item.title), None)
        if matched:
            if item.start_year is not None and (matched.start_year is None or item.start_year < matched.start_year):
                matched.start_year = item.start_year
            if item.end_year is not None and (matched.end_year is None or item.end_year > matched.end_year):
                matched.end_year = item.end_year
            if matched.longitude is None and item.longitude is not None:
                matched.longitude, matched.latitude = item.longitude, item.latitude
                matched.spatial_precision = item.spatial_precision
            if not matched.address:
                matched.address = item.address
            matched.people = unique(matched.people + item.people + infer_explicit_people(f"{matched.title} {matched.description}"))
            matched.organizations = unique(matched.organizations + item.organizations + infer_explicit_organizations(f"{matched.title} {matched.description}"))
            continue
        copied = HistoricalFeature(**asdict(item))
        copied.people = unique(copied.people + infer_explicit_people(f"{copied.title} {copied.description}"))
        copied.organizations = unique(copied.organizations + infer_explicit_organizations(f"{copied.title} {copied.description}"))
        result.append(copied)
    return result


def rank_features(features: list[HistoricalFeature], candidate: PlaceCandidate, address: str) -> list[HistoricalFeature]:
    house = parse_public_address(address)["house_number"].replace("号", "")
    terms = unique([candidate.canonical_name] + candidate.historical_names + candidate.modern_names)

    def score(item: HistoricalFeature) -> tuple[int, int, int, str]:
        text = f"{item.title} {item.description} {item.address}"
        place_hits = sum(1 for term in terms if term and term in text)
        house_hit = 1 if house and house in text else 0
        coordinate = 1 if item.longitude is not None and item.latitude is not None else 0
        return house_hit, place_hits, coordinate, item.title

    unique_features: dict[str, HistoricalFeature] = {}
    for item in features:
        unique_features[item.source_uri or item.feature_id] = item
    return sorted(unique_features.values(), key=score, reverse=True)[:12]


def build_place_claims(candidate: PlaceCandidate, features: list[HistoricalFeature], *, address: str = "") -> list[HistoricalClaim]:
    claims: list[HistoricalClaim] = []
    supported_claims: list[HistoricalClaim] = []
    query_house = parse_public_address(address)["house_number"].replace("号", "")
    for item in features:
        text = f"{item.title} {item.description} {item.address}"
        names = unique([candidate.canonical_name] + candidate.historical_names + candidate.modern_names)
        entity_match = any(name and name in text for name in names)
        temporal_relation = item.feature_type == "event" and (item.start_year is not None or item.end_year is not None)
        spatial_relation = item.feature_type == "building" and bool(item.address)
        relation_match = temporal_relation or spatial_relation
        supported = entity_match and relation_match and bool(item.source_uri)
        # A single record is promoted to a direct fact only when the user's
        # public house number also matches. Other relevant records remain
        # contextual nodes until multiple independent sources support a
        # composite place claim.
        item_house = parse_public_address(item.address)["house_number"].replace("号", "")
        exact_house = bool(query_house and item_house and query_house == item_house)
        direct = supported and exact_house
        if item.feature_type == "event":
            claim_text = f"{format_year_range(item.start_year, item.end_year)}，{item.title}与{candidate.canonical_name}形成可核查的地点—事件关系。"
            predicate = "发生于"
        else:
            claim_text = f"{item.title}位于{item.address or candidate.canonical_name}，可作为该地点历史空间的实物线索。"
            predicate = "位于"
        claim = HistoricalClaim(
            claim_id=stable_id("claim", item.feature_id),
            subject=item.title,
            predicate=predicate,
            object=candidate.canonical_name,
            text=claim_text,
            evidence_ids=[item.feature_id],
            support_level="direct" if direct else "context",
            audit_status="passed" if supported else "review",
            confidence=0.9 if direct and item.live_api else 0.84 if direct else 0.7 if supported else 0.52,
            start_year=item.start_year,
            end_year=item.end_year,
        )
        claims.append(claim)
        if supported:
            supported_claims.append(claim)
    independent = []
    seen_sources: set[str] = set()
    for claim, feature in zip(claims, features):
        if claim not in supported_claims or not feature.source_uri or feature.source_uri in seen_sources:
            continue
        independent.append(claim)
        seen_sources.add(feature.source_uri)
    if len(independent) >= 2:
        claims.append(HistoricalClaim(
            claim_id="claim-place-synthesis",
            subject=candidate.canonical_name,
            predicate="连接",
            object="多个历史事件与建筑",
            text=f"围绕{candidate.display_name}，至少有 {len(independent)} 条独立来源把同一地点连接到不同年代的事件或建筑。",
            evidence_ids=unique([evidence_id for item in independent[:4] for evidence_id in item.evidence_ids]),
            support_level="direct",
            audit_status="passed",
            confidence=min(0.94, 0.78 + len(independent) * 0.025),
        ))
    return claims


def build_evidence_cards(features: list[HistoricalFeature], claims: list[HistoricalClaim]) -> list[dict[str, Any]]:
    claim_map: dict[str, list[str]] = {}
    for claim in claims:
        for evidence_id in claim.evidence_ids:
            claim_map.setdefault(evidence_id, []).append(claim.claim_id)
    cards = []
    for item in features:
        is_shlibrary = "data.library.sh.cn/" in (item.source_uri or "")
        cards.append({
            "evidence_id": item.feature_id,
            "title": item.title,
            "description": item.description,
            "source_title": item.source_title,
            "source_uri": item.source_uri,
            "address": item.address,
            "time_label": format_year_range(item.start_year, item.end_year),
            "start_year": item.start_year,
            "end_year": item.end_year,
            "feature_type": item.feature_type,
            "spatial_precision": item.spatial_precision,
            "people": item.people,
            "organizations": item.organizations,
            "claim_ids": claim_map.get(item.feature_id, []),
            "live_api": item.live_api,
            "provider": "上海图书馆" if is_shlibrary else "公开辅助来源",
            "source_mode": "live_api" if item.live_api else "reviewed_official_snapshot" if is_shlibrary else "public_auxiliary",
            "lineage": {
                "provider": "Shanghai Library" if is_shlibrary else item.source_title,
                "official_uri": item.source_uri,
                "evidence_id": item.feature_id,
                "normalization": "ContextLens place investigation v1",
            },
        })
    return cards


def build_archive_network(
    candidate: PlaceCandidate,
    features: list[HistoricalFeature],
    person_records: dict[str, list[dict[str, Any]]],
    organization_records: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build an evidence-bound place/event/person/institution graph.

    A name match is not enough to choose a person authority record. Multiple
    exact matches stay ambiguous and expose no biography as if it were proven.
    """
    place_id = f"place:{candidate.candidate_id}"
    road_evidence_id = stable_id("road-profile", candidate.source_uri or candidate.canonical_name)
    nodes: list[dict[str, Any]] = [{
        "node_id": place_id,
        "node_type": "place",
        "name": candidate.display_name,
        "description": candidate.match_reason,
        "source_uri": candidate.source_uri,
        "match_status": candidate.resolution_status,
        "evidence_ids": [road_evidence_id] if candidate.source_uri else [],
    }]
    links: list[dict[str, Any]] = []
    supplemental: list[dict[str, Any]] = []
    if candidate.source_uri:
        supplemental.append({
            "evidence_id": road_evidence_id,
            "title": candidate.canonical_name,
            "description": candidate.match_reason,
            "source_title": "上海地名志·道路实体",
            "source_uri": candidate.source_uri,
            "address": candidate.house_number,
            "time_label": format_year_range(candidate.valid_from, candidate.valid_to),
            "start_year": candidate.valid_from,
            "end_year": candidate.valid_to,
            "feature_type": "road_identity",
            "spatial_precision": "not_applicable",
            "people": [],
            "organizations": [],
            "claim_ids": [],
            "live_api": candidate.candidate_id.startswith("shlib-road"),
            "provider": "上海图书馆",
            "source_mode": "live_api" if candidate.candidate_id.startswith("shlib-road") else "reviewed_official_snapshot",
            "lineage": {"provider": "Shanghai Library", "official_uri": candidate.source_uri, "evidence_id": road_evidence_id, "normalization": "ContextLens road identity v1"},
        })

    feature_people: dict[str, list[str]] = {}
    feature_organizations: dict[str, list[str]] = {}
    for feature in features:
        feature_node_id = f"feature:{feature.feature_id}"
        nodes.append({
            "node_id": feature_node_id,
            "node_type": feature.feature_type,
            "name": feature.title,
            "description": feature.description,
            "source_uri": feature.source_uri,
            "match_status": "source_record",
            "evidence_ids": [feature.feature_id],
        })
        links.append({
            "source": place_id,
            "target": feature_node_id,
            "relation": "发生于" if feature.feature_type == "event" else "位于",
            "evidence_ids": [feature.feature_id],
        })
        for name in feature.people:
            feature_people.setdefault(name, []).append(feature.feature_id)
        for name in feature.organizations:
            feature_organizations.setdefault(name, []).append(feature.feature_id)

    person_nodes: list[dict[str, Any]] = []
    for name, evidence_ids in feature_people.items():
        exact = [item for item in person_records.get(name, []) if clean_text(item.get("fname")) == name]
        match_status = "confirmed" if len(exact) == 1 else "ambiguous" if len(exact) > 1 else "relation_only"
        record = exact[0] if len(exact) == 1 else {}
        uri = canonical_source_uri(clean_text(record.get("uri")))
        person_id = f"person:{stable_id('entity', uri or name)}"
        lifespan = format_year_range(extract_years(record.get("start"), record.get("end"))[0], extract_years(record.get("start"), record.get("end"))[1]) if record else "生卒年待考"
        node = {
            "node_id": person_id,
            "node_type": "person",
            "name": name,
            "description": clean_text(record.get("briefBiography"))[:520] if record else "同名人物尚未完成消歧；仅确认该姓名出现在相关来源中。",
            "speciality": clean_text(record.get("speciality")) if record else "",
            "lifespan": lifespan,
            "source_uri": uri,
            "match_status": match_status,
            "candidate_count": len(exact),
            "evidence_ids": unique(evidence_ids),
        }
        person_nodes.append(node)
        nodes.append(node)
        for evidence_id in unique(evidence_ids):
            links.append({"source": f"feature:{evidence_id}", "target": person_id, "relation": "相关人物", "evidence_ids": [evidence_id]})
        if record and uri:
            profile_id = stable_id("person-profile", uri)
            supplemental.append({
                "evidence_id": profile_id,
                "title": name,
                "description": clean_text(record.get("briefBiography"))[:900],
                "source_title": "上海图书馆人名规范库",
                "source_uri": uri,
                "address": clean_text(record.get("place")),
                "time_label": lifespan,
                "start_year": extract_years(record.get("start"))[0],
                "end_year": extract_years(record.get("end"))[1],
                "feature_type": "person_profile",
                "spatial_precision": "not_applicable",
                "people": [name],
                "organizations": [],
                "claim_ids": [],
                "live_api": True,
                "provider": "上海图书馆",
                "source_mode": "live_api",
                "lineage": {"provider": "Shanghai Library", "official_uri": uri, "evidence_id": profile_id, "normalization": "ContextLens person authority v1"},
            })

    organization_nodes: list[dict[str, Any]] = []
    for name, evidence_ids in feature_organizations.items():
        exact = [item for item in organization_records.get(name, []) if name in organization_names(item)]
        match_status = "confirmed" if len(exact) == 1 else "ambiguous" if len(exact) > 1 else "relation_only"
        record = exact[0] if len(exact) == 1 else {}
        uri = canonical_source_uri(clean_text(record.get("uri")))
        organization_id = f"organization:{stable_id('entity', uri or name)}"
        node = {
            "node_id": organization_id,
            "node_type": "organization",
            "name": name,
            "description": f"来源：{clean_text(record.get('noteOfSource'))}" if record else "机构名称来自相关事件或建筑记录。",
            "source_uri": uri,
            "match_status": match_status,
            "candidate_count": len(exact),
            "evidence_ids": unique(evidence_ids),
        }
        organization_nodes.append(node)
        nodes.append(node)
        for evidence_id in unique(evidence_ids):
            links.append({"source": f"feature:{evidence_id}", "target": organization_id, "relation": "相关机构", "evidence_ids": [evidence_id]})
        if record and uri:
            supplemental.append({
                "evidence_id": stable_id("organization-profile", uri),
                "title": name,
                "description": node["description"],
                "source_title": "上海年华机构名录",
                "source_uri": uri,
                "address": "",
                "time_label": "年代待考",
                "start_year": None,
                "end_year": None,
                "feature_type": "organization_profile",
                "spatial_precision": "not_applicable",
                "people": [],
                "organizations": [name],
                "claim_ids": [],
                "live_api": True,
                "provider": "上海图书馆",
                "source_mode": "live_api",
                "lineage": {"provider": "Shanghai Library", "official_uri": uri, "evidence_id": stable_id("organization-profile", uri), "normalization": "ContextLens organization authority v1"},
            })

    event_count = sum(1 for item in features if item.feature_type == "event")
    building_count = sum(1 for item in features if item.feature_type == "building")
    datasets = [
        {"dataset_id": "road", "title": "上海地名志·道路", "available_label": "1万余地名", "count": 1 if candidate.source_uri else 0, "active": bool(candidate.source_uri)},
        {"dataset_id": "event", "title": "上海历史文化事件", "available_label": "1.5万余事件", "count": event_count, "active": event_count > 0},
        {"dataset_id": "building", "title": "上海优秀历史建筑", "available_label": "1086处", "count": building_count, "active": building_count > 0},
        {"dataset_id": "person", "title": "人名规范库", "available_label": "135万余人", "count": len(person_nodes), "active": bool(person_nodes)},
        {"dataset_id": "organization", "title": "上海年华机构名录", "available_label": "2.1万余机构", "count": len(organization_nodes), "active": bool(organization_nodes)},
    ]
    return {
        "stats": {
            "node_count": len(nodes),
            "link_count": len(links),
            "person_count": len(person_nodes),
            "organization_count": len(organization_nodes),
            "event_count": event_count,
            "building_count": building_count,
        },
        "datasets": datasets,
        "nodes": nodes,
        "links": links,
        "people": person_nodes,
        "organizations": organization_nodes,
        "supplemental_evidence": supplemental,
    }


def organization_names(item: dict[str, Any]) -> list[str]:
    values = item.get("name")
    if not isinstance(values, list):
        values = [values]
    names: list[str] = []
    for value in values:
        if isinstance(value, dict):
            if value.get("@language") in {"chs", "zh", "zh-CN", None}:
                names.append(clean_text(value.get("@value") or value.get("value")))
        else:
            text = clean_text(value)
            if text.endswith("@chs"):
                names.append(text[:-4])
            elif "@" not in text:
                names.append(text)
    return unique(names)


def feature_to_timeline(item: HistoricalFeature) -> dict[str, Any]:
    return {
        "feature_id": item.feature_id,
        "title": item.title,
        "start_year": item.start_year,
        "end_year": item.end_year,
        "time_label": format_year_range(item.start_year, item.end_year),
        "type": item.feature_type,
        "address": item.address,
        "source_uri": item.source_uri,
        "spatial_precision": item.spatial_precision,
    }


def feature_sort_key(item: HistoricalFeature) -> tuple[int, str]:
    return (item.start_year if item.start_year is not None else 9999, item.title)


def format_year_range(start: int | None, end: int | None) -> str:
    if start and end and start != end:
        return f"{start}—{end}年"
    if start:
        return f"{start}年"
    if end:
        return f"截至{end}年"
    return "年代待考"


def build_summary(candidate: PlaceCandidate, features: list[HistoricalFeature], direct_claims: list[HistoricalClaim]) -> str:
    if not direct_claims:
        return f"已识别{candidate.display_name}，但目前没有足够的直接来源形成确定结论。"
    dated = [item for item in features if item.start_year]
    span = ""
    if dated:
        years = [item.start_year for item in dated if item.start_year]
        span = f"，时间线覆盖 {min(years)}—{max(years)} 年"
    return f"已围绕{candidate.display_name}建立 {len(features)} 个时空节点和 {len(direct_claims)} 条可核查主张{span}。"


def feature_bounds(features: list[HistoricalFeature]) -> list[float] | None:
    points = [(item.longitude, item.latitude) for item in features if item.longitude is not None and item.latitude is not None]
    if not points:
        return None
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return [min(lons), min(lats), max(lons), max(lats)]


def feature_center(features: list[HistoricalFeature]) -> list[float]:
    points = [(item.longitude, item.latitude) for item in features if item.longitude is not None and item.latitude is not None]
    if not points:
        return [121.4737, 31.2304]
    return [sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)]


def public_address_label(address: str) -> str:
    parsed = parse_public_address(address)
    return f"{parsed['place_term']}{parsed['house_number']}" if parsed["place_term"] else "未识别地址"


def hash_private_query(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:20]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("@value", "value", "label", "name"):
            if key in value:
                return clean_text(value[key])
        return ""
    if isinstance(value, list):
        values = [clean_text(item) for item in value]
        return "；".join(item for item in values if item)
    return re.sub(r"\s+", " ", str(value)).strip()


def to_float(value: Any) -> float | None:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if -180 <= number <= 180 else None


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def report_progress(callback: Callable[[str, int, str], None] | None, stage: str, progress: int, message: str) -> None:
    if callback:
        callback(stage, progress, message)


class InvestigationStore:
    """Small in-memory job store so progress reflects real backend stages."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="contextlens-place")

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "status": "queued",
            "stage": "queued",
            "progress": 4,
            "message": "调查已进入队列",
            "result": None,
            "error": "",
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._run, job_id, payload)
        return self.public_job(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return self.public_job(job) if job else None

    def completed_result(self, job_id: str) -> dict[str, Any] | None:
        """Return server-side evidence for optional tools without client re-upload."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.get("status") != "complete" or not isinstance(job.get("result"), dict):
                return None
            return job["result"]

    def _run(self, job_id: str, payload: dict[str, Any]) -> None:
        self._update(job_id, "resolving", 14, "正在确认地点身份")
        try:
            result = investigate_address(
                payload.get("candidate") or {},
                address=str(payload.get("address") or ""),
                era_hint=payload.get("era_hint"),
                allow_live=bool(payload.get("allow_live", True)),
                progress=lambda stage, progress, message: self._update(job_id, stage, progress, message),
            )
            with self._lock:
                job = self._jobs[job_id]
                job.update({"status": "complete", "stage": "complete", "progress": 100, "message": "城市记忆档案已完成", "result": result})
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job.update({"status": "failed", "stage": "failed", "progress": 100, "message": "调查未完成", "error": f"{type(exc).__name__}: {exc}"})

    def _update(self, job_id: str, stage: str, progress: int, message: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update({"status": stage, "stage": stage, "progress": progress, "message": message})

    @staticmethod
    def public_job(job: dict[str, Any]) -> dict[str, Any]:
        return {key: job.get(key) for key in ("id", "status", "stage", "progress", "message", "result", "error", "created_at")}


INVESTIGATION_STORE = InvestigationStore()
