from __future__ import annotations

"""Rights-aware visual sources used by the public street dossiers.

These records are contextual visual evidence, not proof of historical claims.  An
asset is displayable only when its reusable image and licence are explicit.
"""

from typing import Any


MEDIA_ASSETS: list[dict[str, Any]] = [
    {
        "asset_id": "commons-joffre-1930s", "roads": ["霞飞路", "淮海中路"], "kind": "photo", "year": 1932,
        "title": "1930年代的霞飞路", "description": "画面可见霞飞路街景；原文件据国泰大戏院开幕后判断为1932年以后。",
        "title_en": "Avenue Joffre in the 1930s", "description_en": "A street view of Avenue Joffre; the collection dates it after the 1932 opening of the Cathay Theatre.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Avenue%20Joffre%20in%20the%201930s.jpg?width=1600",
        "source_url": "https://commons.wikimedia.org/wiki/File:Avenue_Joffre_in_the_1930s.jpg",
        "provider": "Wikimedia Commons", "creator": "作者不详", "license": "Public domain (China/United States)",
        "attribution": "Avenue Joffre in the 1930s, Wikimedia Commons", "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-petain-1920s", "roads": ["衡山路", "贝当路"], "kind": "photo", "year": 1925,
        "title": "1920年代的贝当路", "description": "贝当路（今衡山路）的历史街景，适合观察道路尺度、树木与沿街建筑关系。",
        "title_en": "Avenue Pétain in the 1920s", "description_en": "A historical view of today’s Hengshan Road, showing its scale, trees and relationship to the buildings along it.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Avenue%20Petain.jpg?width=1600",
        "source_url": "https://commons.wikimedia.org/wiki/File:Avenue_Petain.jpg", "provider": "Virtual Shanghai / Wikimedia Commons",
        "creator": "作者不详", "license": "Public domain", "attribution": "Avenue Petain, Virtual Shanghai / Wikimedia Commons",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-shaanxi-2014", "roads": ["陕西南路", "咸阳路"], "kind": "photo", "year": 2014,
        "title": "陕西南路街景", "description": "陕西南路新乐路以北的当代街景，用于观察历史住宅街区延续至今的道路环境。",
        "title_en": "South Shaanxi Road streetscape", "description_en": "A contemporary view north of Xinle Road, included to examine how the historic residential setting continues today.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/South%20Shanxi%20Rd.%20Shanghai.JPG?width=1600",
        "source_url": "https://commons.wikimedia.org/wiki/File:South_Shanxi_Rd._Shanghai.JPG", "provider": "Wikimedia Commons",
        "creator": "Livelikerw", "license": "CC BY-SA 3.0", "attribution": "Livelikerw, South Shanxi Rd. Shanghai, CC BY-SA 3.0",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-wukang-2016", "roads": ["武康路", "福开森路", "淮海中路"], "kind": "photo", "year": 2016,
        "title": "武康路近淮海路", "description": "武康路与淮海中路附近的当代街景，可与历史地图和旧路名并读。",
        "title_en": "Wukang Road near Huaihai Road", "description_en": "A contemporary streetscape near Huaihai Middle Road, paired with historical names and maps of the area.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Wukang%20Road%20near%20Huaihai%20Road,%20Shanghai.jpg?width=1600",
        "source_url": "https://commons.wikimedia.org/wiki/File:Wukang_Road_near_Huaihai_Road,_Shanghai.jpg",
        "provider": "Wikimedia Commons", "creator": "SSYoung", "license": "CC BY-SA 4.0",
        "attribution": "SSYoung, Wukang Road near Huaihai Road, Shanghai, CC BY-SA 4.0", "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "loc-nanking-road", "roads": ["南京路", "南京东路"], "kind": "photo", "year": 1917,
        "title": "On the Nanking Road, Shanghai", "description": "美国国会图书馆 Bain Collection 收藏的南京路街景。馆藏年代字段为约1910—1920。",
        "title_en": "On the Nanking Road, Shanghai", "description_en": "A Nanking Road street scene from the Library of Congress Bain Collection, catalogued to approximately 1910–1920.",
        "image_url": "https://cdn.loc.gov/service/pnp/ggbain/22500/22594v.jpg",
        "source_url": "https://www.loc.gov/item/2014702545/", "provider": "Library of Congress", "creator": "Bain News Service",
        "license": "No known restrictions on publication (Bain Collection)", "attribution": "Bain News Service, Library of Congress, LC-DIG-ggbain-22594",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-duolun-250", "roads": ["多伦路", "窦乐安路"], "kind": "photo", "year": 2007,
        "title": "多伦路250号", "description": "多伦路250号的街景，用于观察文化街区改造后的道路尺度与沿街建筑。",
        "title_en": "250 Duolun Road", "description_en": "A view of 250 Duolun Road, included to examine the street scale and buildings after its cultural-district renewal.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/250%20Duolun%20Road%20Shanghai.jpg?width=1400",
        "source_url": "https://commons.wikimedia.org/wiki/File:250_Duolun_Road_Shanghai.jpg", "provider": "Wikimedia Commons",
        "creator": "TIY", "license": "Public domain", "attribution": "TIY, 250 Duolun Road Shanghai, public domain",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-sichuan-2012", "roads": ["四川北路", "北四川路"], "kind": "photo", "year": 2012,
        "title": "四川北路街景", "description": "2012年的四川北路街景，用于观察商业道路与沿街建筑的当代状态。",
        "title_en": "North Sichuan Road streetscape", "description_en": "A 2012 street view showing the contemporary commercial road and its building frontage.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/North%20Sichuan%20Road%20Shanghai%208-6-12.jpg?width=1400",
        "source_url": "https://commons.wikimedia.org/wiki/File:North_Sichuan_Road_Shanghai_8-6-12.jpg", "provider": "Wikimedia Commons",
        "creator": "Yhz1221", "license": "CC BY-SA 3.0", "attribution": "Yhz1221, North Sichuan Road Shanghai, CC BY-SA 3.0",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-ohel-moishe-2011", "roads": ["长阳路", "华德路"], "kind": "photo", "year": 2011,
        "title": "摩西会堂", "description": "长阳路62号摩西会堂的当代外观，是提篮桥历史文化街区犹太社群历史的重要空间见证。",
        "title_en": "Ohel Moishe Synagogue", "description_en": "The synagogue at 62 Changyang Road is a key spatial witness to Jewish life in the Tilanqiao historic district.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ohel%20Moishe%20Synagogue%20Shanghai.jpg?width=1400",
        "source_url": "https://commons.wikimedia.org/wiki/File:Ohel_Moishe_Synagogue_Shanghai.jpg", "provider": "Wikimedia Commons",
        "creator": "Harvey Barrison", "license": "CC BY-SA 2.0", "attribution": "Harvey Barrison, Ohel Moishe Synagogue Shanghai, CC BY-SA 2.0",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
    {
        "asset_id": "commons-bund-1891", "roads": ["外滩", "中山东一路"], "kind": "photo", "year": 1891,
        "title": "1891年的外滩16至19号", "description": "画面记录外滩16至19号一带的早期江岸建筑，可与后来形成的连续街墙对照。",
        "title_en": "The Bund, Nos. 16–19, in 1891", "description_en": "An early view of buildings 16–19, useful for comparison with the continuous street wall that formed later.",
        "image_url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/View%20of%20no.16,%20no.%2017,%20no.18%20and%20no.19,%20The%20Bund,%20Shanghai.jpg?width=1400",
        "source_url": "https://commons.wikimedia.org/wiki/File:View_of_no.16,_no._17,_no.18_and_no.19,_The_Bund,_Shanghai.jpg", "provider": "Historical Photographs of China / Wikimedia Commons",
        "creator": "作者不详", "license": "Public domain", "attribution": "View of Nos. 16–19, The Bund, Historical Photographs of China / Wikimedia Commons",
        "rights_status": "displayable", "evidence_role": "contextual",
    },
]


def media_for_street(names: list[str]) -> list[dict[str, Any]]:
    terms = {name.strip() for name in names if name and name.strip()}
    return [dict(asset) for asset in MEDIA_ASSETS if terms.intersection(asset["roads"])]


def validate_media_registry() -> list[str]:
    errors: list[str] = []
    required = {"asset_id", "roads", "kind", "title", "source_url", "provider", "license", "attribution", "rights_status", "evidence_role"}
    for asset in MEDIA_ASSETS:
        missing = required.difference(asset)
        if missing:
            errors.append(f"{asset.get('asset_id', '?')}: missing {sorted(missing)}")
        if asset.get("rights_status") == "displayable" and not asset.get("image_url"):
            errors.append(f"{asset.get('asset_id', '?')}: displayable asset has no image")
        if asset.get("evidence_role") != "contextual":
            errors.append(f"{asset.get('asset_id', '?')}: visual must not be promoted to claim evidence")
    return errors
