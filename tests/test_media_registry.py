from app.media_registry import media_for_street, validate_media_registry


def test_visual_assets_have_complete_rights_metadata():
    assert validate_media_registry() == []


def test_multiple_streets_have_rights_aware_visuals():
    assert media_for_street(["霞飞路"])
    assert media_for_street(["武康路"])
    assert media_for_street(["南京东路"])


def test_visuals_are_context_not_claim_evidence():
    assert all(item["evidence_role"] == "contextual" for item in media_for_street(["霞飞路"]))
