from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models import CuratedInteraction, HistoricalMapLayer, LandmarkScene, StoryChapter


VIRTUAL_SHANGHAI_TERMS = "https://www.virtualshanghai.net/Project/Rules_and_Conditions"
VIRTUAL_SHANGHAI_CATALOG = "https://www.virtualshanghai.net/Maps/Source?rp=900"


def _map(
    map_id: str,
    year: int,
    title: str,
    source_url: str,
    *,
    provider: str = "Virtual Shanghai",
    scope: str = "上海城市",
    kind: str = "历史地图原件",
    access: str = "external_catalog",
) -> dict[str, Any]:
    return {
        "map_id": map_id,
        "year": year,
        "title": title,
        "provider": provider,
        "scope": scope,
        "kind": kind,
        "access": access,
        "source_url": source_url,
        "terms_url": VIRTUAL_SHANGHAI_TERMS if provider == "Virtual Shanghai" else source_url,
        "overlay_ready": False,
    }


# A discovery catalog, not a claim that every scan is georeferenced. The UI
# keeps these original maps separate from the dynamic OHM vector layer.
HISTORICAL_MAP_CATALOG: list[dict[str, Any]] = [
    _map("vs-754", 1810, "上海县城图（约1800—1820）", "https://www.virtualshanghai.net/Maps/Source?ID=754", scope="上海县城"),
    _map("vs-30", 1855, "上海英租界地面图", "https://www.virtualshanghai.net/Maps/Source?ID=30", scope="英租界"),
    _map("vs-345", 1862, "City and Environs of Shanghai", "https://www.virtualshanghai.net/Maps/Source?ID=345"),
    _map("vs-344", 1875, "上海县城厢租界全图", "https://www.virtualshanghai.net/Maps/Source?ID=344"),
    _map("vs-261", 1884, "上海县城厢租界全图", "https://www.virtualshanghai.net/Maps/Source?ID=261"),
    _map("vs-76", 1904, "Plan of Shanghai", "https://www.virtualshanghai.net/Maps/Source?ID=76"),
    _map("vs-260", 1910, "实测上海城厢租界图", "https://www.virtualshanghai.net/Maps/Source?ID=260"),
    _map("vs-72", 1918, "Map of Shanghai", "https://www.virtualshanghai.net/Maps/Source?ID=72"),
    _map("vs-272", 1926, "公共租界中央区与法租界街道图", "https://www.virtualshanghai.net/Maps/Source?ID=272"),
    _map("vs-242", 1932, "上海市街图", "https://www.virtualshanghai.net/Maps/Source?ID=242"),
    _map("vs-100", 1934, "法租界地图", "https://www.virtualshanghai.net/Maps/Source?ID=100", scope="法租界"),
    _map("vs-230", 1939, "上海电车线路图", "https://www.virtualshanghai.net/Maps/Source?ID=230", scope="城市交通"),
    _map("princeton-1943", 1943, "Plan of Shanghai · Sheet 1", "https://geodiscovery.uwm.edu/catalog/princeton-8623j0184", provider="Princeton University / AGSL", kind="公共 IIIF 地图", access="public_iiif"),
    _map("vs-341", 1946, "上海市街道详图", "https://www.virtualshanghai.net/Maps/Source?ID=341"),
    _map("vs-249", 1956, "上海市市区图", "https://www.virtualshanghai.net/Maps/Source?ID=249"),
    _map("vs-84", 1972, "Shanghai Area", "https://www.virtualshanghai.net/Maps/Source?ID=84"),
    _map("vs-733", 1987, "上海通用版最新旅游图", "https://www.virtualshanghai.net/Maps/Source?ID=733"),
    _map("vs-734", 1994, "浦东新区陆家嘴金融贸易区示意图", "https://www.virtualshanghai.net/Maps/Source?ID=734", scope="浦东"),
    _map("vs-262", 2003, "上海城区图", "https://www.virtualshanghai.net/Maps/Source?ID=262"),
    _map("vs-735", 2005, "上海城区交通图", "https://www.virtualshanghai.net/Maps/Source?ID=735", scope="城市交通"),
]


ERA_GUIDE = [
    {"from_year": 1600, "to_year": 1842, "label": "县城与水网", "note": "可从县城图和早期河道、城厢材料理解开埠前空间。"},
    {"from_year": 1843, "to_year": 1899, "label": "开埠与租界扩展", "note": "租界、码头和新道路逐步改变城厢边界。"},
    {"from_year": 1900, "to_year": 1926, "label": "近代市政成形", "note": "道路、电车、公共设施与分区地图迅速增多。"},
    {"from_year": 1927, "to_year": 1948, "label": "都市文化与战时重组", "note": "商业、出版、文化机构与战争空间并存。"},
    {"from_year": 1949, "to_year": 1978, "label": "道路更名与城市建设", "note": "道路名称、机构功能和城市治理体系发生变化。"},
    {"from_year": 1979, "to_year": 1989, "label": "改革开放初期", "note": "旅游图与交通图记录城市重新连接世界。"},
    {"from_year": 1990, "to_year": 2009, "label": "浦东开发与快速扩张", "note": "新区规划、轨道交通和跨江发展成为主线。"},
    {"from_year": 2010, "to_year": datetime.now(UTC).year, "label": "更新与历史保护", "note": "当代底图用于定位，历史建筑与旧址仍需回到来源复核。"},
]


LANDMARK_MODELS = [
    {
        "model_id": "customs-house",
        "year": 1927,
        "title": "外滩海关大楼",
        "model_type": "clock-tower",
        "height_m": None,
        "source_url": "https://www.shanghai.gov.cn/gwk/search/content/42925f1923764d98bfa7198785e56512",
        "note": "依据公开建成年代制作的概念体量，不是测绘级复原。",
    },
    {
        "model_id": "peace-hotel",
        "year": 1929,
        "title": "沙逊大厦 / 和平饭店北楼",
        "model_type": "pyramid-roof",
        "height_m": 77,
        "source_url": "https://www.shanghai.gov.cn/nw5827/20200905/0001-5827_632318.html",
        "note": "体量突出金字塔形屋顶；不替代建筑测绘资料。",
    },
    {
        "model_id": "oriental-pearl",
        "year": 1994,
        "title": "东方明珠",
        "model_type": "pearl-tower",
        "height_m": 468,
        "source_url": "https://english.shanghai.gov.cn/en-Latest-WhatsNew/20240930/57966196af434811aec2d86ba75fc7a6.html",
        "note": "以球体和塔身表达轮廓的概念模型。",
    },
    {
        "model_id": "jinmao",
        "year": 1998,
        "title": "金茂大厦",
        "model_type": "tiered-tower",
        "height_m": 420.5,
        "source_url": "https://en.shanghaitower.com/news_2/34.html",
        "note": "以逐级收分表达轮廓的概念模型。",
    },
    {
        "model_id": "swfc",
        "year": 2008,
        "title": "上海环球金融中心",
        "model_type": "portal-tower",
        "height_m": 492,
        "source_url": "https://en.shanghaitower.com/news_2/34.html",
        "note": "以顶部开口表达轮廓的概念模型。",
    },
    {
        "model_id": "shanghai-tower",
        "year": 2014,
        "title": "上海中心大厦",
        "model_type": "twist-tower",
        "height_m": 632,
        "source_url": "https://www.shanghaitower.com/ProjectIntroduction.html",
        "note": "以旋转收分表达轮廓的概念模型；2014年底土建竣工。",
    },
]


CURATED_MAP_LAYERS = [
    HistoricalMapLayer(
        map_id="commons-1855",
        year=1855,
        title="上海租界图（1855，叠加1910街道）",
        source_url="https://commons.wikimedia.org/wiki/File:Map_Shanghai_1855.jpg",
        provider="Wikimedia Commons",
        license="Public Domain Mark",
        attribution="Unknown author / Wikimedia Commons",
        image_url="https://commons.wikimedia.org/wiki/Special:Redirect/file/Map Shanghai 1855.jpg?width=1400",
        overlay_status="side_by_side",
    ),
    HistoricalMapLayer(
        map_id="commons-1916",
        year=1916,
        title="Shanghai around 1910（1916年出版）",
        source_url="https://commons.wikimedia.org/wiki/File:Shanghai_ca_1910.JPG",
        provider="Nordisk familjebok / Wikimedia Commons",
        license="Public domain",
        attribution="Nordisk familjebok / Wikimedia Commons",
        image_url="https://commons.wikimedia.org/wiki/Special:Redirect/file/Shanghai ca 1910.JPG?width=1400",
        overlay_status="side_by_side",
    ),
    HistoricalMapLayer(
        map_id="princeton-1943",
        year=1943,
        title="Plan of Shanghai · Sheet 1",
        source_url="https://geodiscovery.uwm.edu/catalog/princeton-8623j0184",
        provider="Princeton University Library / AGSL",
        license="Public content; rights status NKC",
        attribution="Army Map Service / Princeton University Library",
        image_url="https://iiif-cloud.princeton.edu/iiif/2/42%2F8a%2F93%2F428a930342fb4c36ae9b4ecdc57eae37%2Fintermediate_file/full/1600,/0/default.jpg",
        iiif_manifest_url="https://figgy.princeton.edu/concern/scanned_maps/9691c7cc-726c-4a44-9f77-0a9867178fb8/manifest",
        annotation_url="/assets/data/princeton-1943-georef.json",
        # The bundled annotation is an explicit review draft. Its four coarse
        # control points have not passed a measured residual-error audit, so the
        # public experience must keep the scan side by side rather than warping
        # it over present-day streets.
        overlay_status="review_only",
    ),
    HistoricalMapLayer(
        map_id="commons-1954",
        year=1954,
        title="Shanghai Map 1954",
        source_url="https://commons.wikimedia.org/wiki/File:Shanghai_Map_1954.jpg",
        provider="US Army Corps of Engineers / Wikimedia Commons",
        license="Public domain (US federal work)",
        attribution="US Army Corps of Engineers / Wikimedia Commons",
        image_url="https://commons.wikimedia.org/wiki/Special:Redirect/file/Shanghai Map 1954.jpg?width=1600",
        overlay_status="side_by_side",
    ),
]


LANDMARK_SCENES = [
    LandmarkScene("xiafei-block", "霞飞路街廓体量", "Avenue Joffre block massing", 121.4669, 31.2170, 1934, None, 24, 86, 22, "archive-block", "C", "门牌位置为道路范围定位；仅表达街廓相对体量。", "https://data.library.sh.cn/authority/event/04jaae3kvaff22d1"),
    LandmarkScene("customs-house", "外滩海关大楼", "Customs House", 121.4903, 31.2398, 1927, None, 90, 34, 44, "clock-tower", "C", "坐标和建成年代可核验；展示高度为相对体量。", "https://www.shanghai.gov.cn/gwk/search/content/42925f1923764d98bfa7198785e56512"),
    LandmarkScene("peace-hotel", "和平饭店北楼", "Peace Hotel North Building", 121.4906, 31.2409, 1929, None, 77, 42, 34, "pyramid-roof", "B", "坐标、建成年代与77米高度可核验；立面细节未复原。", "https://www.shanghai.gov.cn/nw5827/20200905/0001-5827_632318.html"),
    LandmarkScene("oriental-pearl", "东方明珠", "Oriental Pearl Tower", 121.4953, 31.2417, 1994, None, 468, 24, 24, "pearl-tower", "A", "位置、建成年代与468米高度采用官方资料。", "https://english.shanghai.gov.cn/en-Latest-WhatsNew/20240930/57966196af434811aec2d86ba75fc7a6.html"),
    LandmarkScene("jinmao", "金茂大厦", "Jin Mao Tower", 121.5056, 31.2353, 1998, None, 420.5, 46, 46, "tiered-tower", "A", "位置、年份与高度可核验，模型为简化轮廓。", "https://en.shanghaitower.com/news_2/34.html"),
    LandmarkScene("swfc", "上海环球金融中心", "Shanghai World Financial Center", 121.5074, 31.2346, 2008, None, 492, 48, 48, "portal-tower", "A", "位置、年份与高度可核验，模型为简化轮廓。", "https://en.shanghaitower.com/news_2/34.html"),
    LandmarkScene("shanghai-tower", "上海中心大厦", "Shanghai Tower", 121.5011, 31.2336, 2014, None, 632, 58, 58, "twist-tower", "A", "位置与632米高度采用官方资料；模型仅表达旋转收分。", "https://www.shanghaitower.com/ProjectIntroduction.html"),
]


DIRECTOR_CHAPTERS = [
    StoryChapter("arrival", datetime.now(UTC).year, "从今天返回旧址", "Return to the old address", "城市的过去没有消失，它仍藏在道路、建筑与人的记忆里。", "The city's past remains in its streets, buildings and memories.", 4000, [121.4737, 31.2231], 11.7, 52, -18, ["modern", "landmarks"], ["map-modern"]),
    StoryChapter("road-born", 1915, "一条路经历三个名字", "A road takes three names", "1901年至1915年，这里从西江路、宝昌路走向霞飞路。", "From 1901 to 1915, West River Road became Route Paul Brunat and then Avenue Joffre.", 7000, [121.4669, 31.2170], 14.1, 22, -8, ["historical", "roads"], ["road-identity"]),
    StoryChapter("archive-map", 1943, "原图落回城市", "The archival map returns", "这幅原图尚有配准误差；它帮助辨认街道结构，但不制造精确门牌。", "This scan carries registration error: useful for street structure, not a precise doorstep.", 8000, [121.4669, 31.2170], 15.1, 0, 0, ["historical", "archive"], ["map-princeton-1943"]),
    StoryChapter("kangjian", 1934, "霞飞路436号亮起一盏灯", "A light at 436 Avenue Joffre", "1934年，康健书局在霞飞路436号创办；这条事实可以回到上海图书馆事件数据复核。", "In 1934, Kangjian Bookstore opened at 436 Avenue Joffre, supported by the library event record.", 10000, [121.4669, 31.2170], 16.0, 42, -12, ["historical", "events", "landmarks"], ["kangjian"]),
    StoryChapter("renaming", 1944, "同一条路继续改名", "One road, changing names", "霞飞路随后成为泰山路、林森中路，并在1950年定名淮海中路。", "Avenue Joffre became Taishan Road, Linsen Middle Road, then Huaihai Middle Road in 1950.", 9000, [121.4669, 31.2170], 14.6, 30, 8, ["historical", "roads"], ["road-identity"]),
    StoryChapter("return", datetime.now(UTC).year, "把记忆带回今天", "Bring the memory home", "现代三维城市只负责定位；历史结论仍然由来源、时间和不确定性共同限定。", "The modern 3D city locates the place; sources and uncertainty still bound every historical claim.", 7000, [121.4737, 31.2231], 12.8, 55, -20, ["modern", "landmarks", "evidence"], ["map-modern"]),
]


CURATED_INTERACTIONS = [
    CuratedInteraction("find-joffre", "map_hotspot", "在原图中找到霞飞路", "Find Avenue Joffre", "点击你认为霞飞路经过的位置；需要时可查看提示。", "Select where you think Avenue Joffre ran. Ask for a hint whenever you need it.", ["map-princeton-1943", "road-identity"], {"target_percent": [42, 63], "radius_percent": 12, "hint_after_ms": 6000}, "road-finder"),
    CuratedInteraction("road-relay", "ordered_names", "地名接力", "Road-name relay", "按时间把六个道路名称排成一条连续历史。", "Arrange the six road names into one continuous history.", ["road-identity"], {"items": ["西江路", "宝昌路", "霞飞路", "泰山路", "林森中路", "淮海中路"]}, "name-relay"),
    CuratedInteraction("source-trail", "source_count", "打开三条来源", "Open three sources", "沿证据抽屉打开三条不同来源。", "Open three distinct records from the evidence drawer.", ["road-identity", "kangjian", "map-princeton-1943"], {"required": 3}, "source-trail"),
]


def build_experience(candidate: Any, features: list[Any]) -> dict[str, Any]:
    candidate_name = getattr(candidate, "canonical_name", "")
    flagship = "霞飞路" in candidate_name or "淮海中路" in candidate_name
    feature_ids = {getattr(item, "title", ""): getattr(item, "feature_id", "") for item in features}
    chapters = []
    for chapter in DIRECTOR_CHAPTERS:
        item = chapter.to_dict()
        item["evidence_ids"] = [feature_ids.get("康健书局创办", value) if value == "kangjian" else value for value in item["evidence_ids"]]
        chapters.append(item)
    interactions = [item.to_dict() for item in CURATED_INTERACTIONS]
    landmark_scenes = LANDMARK_SCENES if flagship else [item for item in LANDMARK_SCENES if item.model_id != "xiafei-block"]
    if flagship:
        experience_chapters = chapters
        experience_interactions = interactions
    else:
        located = next(
            (
                item
                for item in features
                if getattr(item, "longitude", None) is not None and getattr(item, "latitude", None) is not None
            ),
            None,
        )
        center = [getattr(located, "longitude", 121.4737), getattr(located, "latitude", 31.2304)]
        focus = next((item for item in features if getattr(item, "start_year", None)), located)
        focus_year = getattr(focus, "start_year", None) or getattr(candidate, "valid_from", None) or 1934
        anchor_ids = [getattr(item, "feature_id", "") for item in features[:3] if getattr(item, "feature_id", "")]
        place_anchor = getattr(candidate, "source_uri", "") or getattr(candidate, "candidate_id", "place")
        experience_chapters = [
            StoryChapter(
                "place-arrival",
                datetime.now(UTC).year,
                f"抵达{candidate_name}",
                f"Arrive at {candidate_name}",
                "先用现代地图建立公开位置，再回到道路实体和历史建筑来源。",
                "Begin with present-day orientation, then return to road and architecture records.",
                21000,
                center,
                14.2,
                48,
                -12,
                ["modern", "landmarks"],
                [place_anchor],
            ).to_dict(),
            StoryChapter(
                "place-evidence",
                focus_year,
                "打开地点证据",
                "Open the place evidence",
                "地图只显示当前证据集中可定位、可计时的节点；空白继续保持空白。",
                "The map shows only locatable, time-bounded records in this evidence set; gaps remain visible.",
                24000,
                center,
                15.2,
                20,
                0,
                ["historical", "events", "buildings"],
                anchor_ids or [place_anchor],
            ).to_dict(),
        ]
        source_trail = interactions[2]
        source_trail["payload"] = {"required": max(1, min(3, len({getattr(item, 'source_uri', '') for item in features if getattr(item, 'source_uri', '')})))}
        source_trail["evidence_ids"] = anchor_ids or [place_anchor]
        experience_interactions = [source_trail]
    return {
        "flagship": flagship,
        "default_duration_seconds": 20,
        "duration_options": [20, 30, 45],
        "chapters": experience_chapters,
        "historical_maps": [item.to_dict() for item in CURATED_MAP_LAYERS],
        "landmark_scenes": [item.to_dict() for item in landmark_scenes],
        "interactions": experience_interactions,
        "comparison": {"year_a": 1934, "year_b": datetime.now(UTC).year, "anchors": [1855, 1901, 1915, 1934, 1944, 1950, 1994, datetime.now(UTC).year]},
        "privacy": {"memory_uploaded": False, "memory_in_url": False, "stamps_storage": "sessionStorage"},
    }


def historical_map_payload(selected_year: int | None = None) -> dict[str, Any]:
    current_year = datetime.now(UTC).year
    year = max(1600, min(current_year, int(selected_year or 1934)))
    ordered = sorted(
        ({**item, "distance": abs(item["year"] - year)} for item in HISTORICAL_MAP_CATALOG),
        key=lambda item: (item["distance"], item["year"]),
    )
    active_era = next((item for item in ERA_GUIDE if item["from_year"] <= year <= item["to_year"]), ERA_GUIDE[-1])
    return {
        "selected_year": year,
        "min_year": 1600,
        "max_year": current_year,
        "dynamic_layer": {
            "title": "OpenHistoricalMap 历史矢量层",
            "style_url": "https://www.openhistoricalmap.org/map-styles/main/main.json",
            "source_url": "https://www.openhistoricalmap.org/",
            "license": "CC0；个别要素可能另有署名要求",
            "coverage_note": "按任意年份过滤；上海细节覆盖随年代和社区录入程度变化。",
        },
        "active_era": active_era,
        "era_guide": ERA_GUIDE,
        "nearest_maps": ordered[:4],
        "catalog": HISTORICAL_MAP_CATALOG,
        "catalog_source": VIRTUAL_SHANGHAI_CATALOG,
        "catalog_terms": VIRTUAL_SHANGHAI_TERMS,
        "landmark_models": LANDMARK_MODELS,
    }
