from app.tool_catalog import CATEGORY_TOOL_ORDER, TOOL_CATALOG, get_home_catalog


def test_catalog_ids_and_paths_are_unique():
    ids = [tool["id"] for tool in TOOL_CATALOG]
    paths = [tool["path"] for tool in TOOL_CATALOG]

    assert len(ids) == len(set(ids))
    assert len(paths) == len(set(paths))


def test_category_tool_order_covers_each_tool_once():
    ordered_ids = [
        tool_id
        for category_ids in CATEGORY_TOOL_ORDER.values()
        for tool_id in category_ids
    ]

    assert len(ordered_ids) == len(set(ordered_ids))
    assert set(ordered_ids) == {tool["id"] for tool in TOOL_CATALOG}


def test_home_catalog_groups_tools_into_sections_and_categories():
    sections = get_home_catalog()

    assert [section["id"] for section in sections] == [
        "cryptography",
        "encoding",
        "text-tools",
        "number-tools",
        "utility",
        "ingress-tools",
        "extra-pages",
    ]

    category_ids = [section["categories"][0]["id"] for section in sections[:5]]
    assert category_ids == [
        "cryptography",
        "encoding",
        "text-tools",
        "number-tools",
        "utility",
    ]

    cryptography_ids = [
        tool["id"] for tool in sections[0]["categories"][0]["tools"]
    ]
    assert "rot" in cryptography_ids
    assert "frequency" in cryptography_ids
    assert "rsa" in cryptography_ids

    ingress_ids = [
        tool["id"] for tool in sections[5]["categories"][0]["tools"]
    ]
    assert set(ingress_ids) == {
        "rot_ex",
        "vigenere_ex",
        "rectangle_ex",
        "charcode_ex",
        "ingress_keywords",
    }
