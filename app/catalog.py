from __future__ import annotations

import json
from pathlib import Path

"""Editorial publication manifest for the public ContextLens catalogue.

Only entries that pass the public full-loop tests belong here.  The broader
resolver index remains useful for research but is deliberately not exposed as
an unrestricted public search surface.
"""

CATALOG = [
    {
        "id": "xiafei", "address": "霞飞路", "name_zh": "霞飞路 · 淮海中路", "name_en": "Avenue Joffre · Huaihai Middle Road",
        "district_zh": "黄浦区 / 徐汇区", "district_en": "Huangpu / Xuhui", "period_zh": "1901—至今", "period_en": "1901—present",
        "intro_zh": "从西江路、宝昌路到霞飞路、林森中路与淮海中路，六次名称阶段串联起商业、出版与都市文化。",
        "intro_en": "Six documented name periods connect the street’s commercial, publishing and metropolitan history.",
        "themes_zh": ["路名沿革", "出版文化", "城市生活"], "themes_en": ["Renaming", "Publishing", "Urban life"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Avenue%20Joffre%20in%20the%201930s.jpg?width=1400", "center": [121.4669, 31.2170],
    },
    {
        "id": "hengshan", "address": "衡山路", "name_zh": "衡山路", "name_en": "Hengshan Road",
        "district_zh": "徐汇区", "district_en": "Xuhui", "period_zh": "1920—至今", "period_en": "1920—present",
        "intro_zh": "旧名贝当路。里弄、公寓与国际礼拜堂共同呈现二十世纪上半叶的居住与公共生活。",
        "intro_en": "Formerly Avenue Pétain, the road preserves layers of lane housing, apartments and public institutions.",
        "themes_zh": ["近代建筑", "公共生活", "路名沿革"], "themes_en": ["Architecture", "Public life", "Renaming"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Avenue%20Petain.jpg?width=1400", "center": [121.4401, 31.2040],
    },
    {
        "id": "chongqing", "address": "重庆南路", "name_zh": "重庆南路", "name_en": "South Chongqing Road",
        "district_zh": "黄浦区", "district_en": "Huangpu", "period_zh": "1923—至今", "period_en": "1923—present",
        "intro_zh": "从灵宝路到重庆南路，万宜坊与重庆公寓记录了近代里弄和集合住宅的发展。",
        "intro_en": "From Lingbao Road to South Chongqing Road, lane housing and apartments trace changing residential life.",
        "themes_zh": ["里弄住宅", "城市更新", "路名沿革"], "themes_en": ["Lane housing", "Urban change", "Renaming"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Shanghai%20Map%201954.jpg?width=1400", "center": [121.4704, 31.2102],
    },
    {
        "id": "shaanxi", "address": "陕西南路", "name_zh": "陕西南路", "name_en": "South Shaanxi Road",
        "district_zh": "黄浦区 / 徐汇区", "district_en": "Huangpu / Xuhui", "period_zh": "1920—至今", "period_en": "1920—present",
        "intro_zh": "亚尔培坊与凡尔登花园呈现花园住宅和里弄并置的街区形态，1946年定名陕西南路。",
        "intro_en": "Garden residences and lane compounds reveal a mixed residential landscape; the present name dates to 1946.",
        "themes_zh": ["花园住宅", "里弄", "路名沿革"], "themes_en": ["Garden residences", "Lane housing", "Renaming"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/South%20Shanxi%20Rd.%20Shanghai.JPG?width=1400", "center": [121.4546, 31.2159],
    },
    {
        "id": "nanjingwest", "address": "南京西路", "name_zh": "南京西路", "name_en": "West Nanjing Road",
        "district_zh": "黄浦区 / 静安区", "district_en": "Huangpu / Jing’an", "period_zh": "1932—至今", "period_en": "1932—present",
        "intro_zh": "旧称静安寺路。静安别墅、国际饭店与公共文化建筑展现商业轴线不断重塑的过程。",
        "intro_en": "Formerly Bubbling Well Road, residential compounds, hotels and civic buildings chart a changing commercial axis.",
        "themes_zh": ["商业街区", "近代建筑", "公共文化"], "themes_en": ["Commerce", "Architecture", "Civic culture"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/2014.11.17.114120%20Buildings%20Nanjing%20West%20Road%20Shanghai.jpg?width=1400", "center": [121.4550, 31.2313],
    },
    {
        "id": "duolun", "address": "多伦路", "name_zh": "多伦路", "name_en": "Duolun Road",
        "district_zh": "虹口区", "district_en": "Hongkou", "period_zh": "1911—至今", "period_en": "1911—present",
        "intro_zh": "从窦乐安路到多伦路，鸿德堂、永安里与文化名人遗迹共同构成一条浓缩的近代文化街区。",
        "intro_en": "From Darroch Road to Duolun Road, churches, lane housing and literary sites form a concentrated modern cultural district.",
        "themes_zh": ["文化名人", "红色遗迹", "近代建筑"], "themes_en": ["Literary culture", "Revolutionary sites", "Architecture"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/250%20Duolun%20Road%20Shanghai.jpg?width=1400", "center": [121.4820, 31.2630],
    },
    {
        "id": "sichuan", "address": "四川北路", "name_zh": "四川北路", "name_en": "North Sichuan Road",
        "district_zh": "虹口区", "district_en": "Hongkou", "period_zh": "1925—至今", "period_en": "1925—present",
        "intro_zh": "北四川路更名为四川北路；永安里与大桥大楼连接起商业、居住和革命活动的多重历史。",
        "intro_en": "Renamed from North Szechuen Road, the street links commerce and residential life with sites of revolutionary activity.",
        "themes_zh": ["商业文化", "里弄住宅", "红色遗迹"], "themes_en": ["Commerce", "Lane housing", "Revolutionary sites"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/North%20Sichuan%20Road%20Shanghai%208-6-12.jpg?width=1400", "center": [121.4810, 31.2680],
    },
    {
        "id": "changyang", "address": "长阳路", "name_zh": "长阳路", "name_en": "Changyang Road",
        "district_zh": "虹口区 / 杨浦区", "district_en": "Hongkou / Yangpu", "period_zh": "1903—至今", "period_en": "1903—present",
        "intro_zh": "旧名华德路。提篮桥监狱与摩西会堂记录了公共治理、犹太社群与战时避难历史。",
        "intro_en": "Formerly Ward Road, the prison and Ohel Moishe Synagogue connect civic administration, Jewish life and wartime refuge.",
        "themes_zh": ["犹太难民", "公共建筑", "历史街区"], "themes_en": ["Jewish refuge", "Civic buildings", "Historic district"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ohel%20Moishe%20Synagogue%20Shanghai.jpg?width=1400", "center": [121.5160, 31.2605],
    },
    {
        "id": "bund", "address": "外滩", "name_zh": "外滩 · 中山东一路", "name_en": "The Bund · East Zhongshan No. 1 Road",
        "district_zh": "黄浦区", "district_en": "Huangpu", "period_zh": "1869—至今", "period_en": "1869—present",
        "intro_zh": "从江岸交通空间到近代金融与公共建筑群，外滩的街墙和天际线记录了上海城市中心的形成。",
        "intro_en": "From riverfront infrastructure to a financial and civic ensemble, the Bund records the making of Shanghai’s urban centre.",
        "themes_zh": ["城市天际线", "金融建筑", "滨江空间"], "themes_en": ["Skyline", "Financial architecture", "Waterfront"],
        "cover": "https://commons.wikimedia.org/wiki/Special:Redirect/file/View%20of%20no.16,%20no.%2017,%20no.18%20and%20no.19,%20The%20Bund,%20Shanghai.jpg?width=1400", "center": [121.4905, 31.2395],
    },
]


def catalog_payload() -> dict:
    relation_path = Path(__file__).resolve().parents[1] / "data/processed/gpu_related_streets.json"
    relation_payload = json.loads(relation_path.read_text()) if relation_path.exists() else {}
    relations = relation_payload.get("related", {})
    streets = []
    for item in CATALOG:
        street = dict(item)
        street["related"] = relations.get(item["id"], [])
        streets.append(street)
    return {
        "version": "2026.08-gpu1", "count": len(streets), "streets": streets,
        "semantic_relations": {
            "available": bool(relations), "method": relation_payload.get("method"),
            "model": relation_payload.get("model"), "generated_at": relation_payload.get("generated_at"),
        },
    }
