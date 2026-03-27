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


def test_home_catalog_contains_only_non_empty_categories():
    sections = get_home_catalog()

    assert sections

    for section in sections:
        assert section["id"]
        assert section["categories"]

        for category in section["categories"]:
            assert category["id"]
            assert category["tools"]


def test_home_catalog_covers_each_tool_once():
    sections = get_home_catalog()

    catalog_tool_ids = [
        tool["id"]
        for section in sections
        for category in section["categories"]
        for tool in category["tools"]
    ]

    assert len(catalog_tool_ids) == len(set(catalog_tool_ids))
    assert set(catalog_tool_ids) == {tool["id"] for tool in TOOL_CATALOG}


def test_niantic_wiki_is_listed_under_remember_ingress():
    sections = get_home_catalog()

    ingress_section = next(
        section for section in sections if section["id"] == "ingress-tools"
    )
    tool_ids = [tool["id"] for tool in ingress_section["categories"][0]["tools"]]

    assert "niantic_wiki" in tool_ids
