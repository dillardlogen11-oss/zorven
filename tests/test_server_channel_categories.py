from zorven.server import normalize_server_structure, parse_channel_lines


def test_parse_channel_lines_supports_category_prefix():
    existing = {
        "announcements": {
            "id": "existing-channel",
            "name": "announcements",
            "description": "Official updates",
            "category": "News",
        }
    }

    parsed = parse_channel_lines("Community > announcements\ngeneral", existing, ["Community"])

    assert parsed[0] == {
        "id": "existing-channel",
        "name": "announcements",
        "description": "Official updates",
        "category": "Community",
    }
    assert parsed[1]["name"] == "general"
    assert parsed[1]["description"] == ""
    assert parsed[1]["category"] == ""
    assert parsed[1]["id"]


def test_parse_channel_lines_preserves_existing_category_without_prefix():
    existing = {
        "general": {
            "id": "general-id",
            "name": "general",
            "description": "Talk about anything",
            "category": "Lobby",
        }
    }

    parsed = parse_channel_lines("general", existing, ["Lobby"])

    assert parsed == [
        {
            "id": "general-id",
            "name": "general",
            "description": "Talk about anything",
            "category": "Lobby",
        }
    ]


def test_normalize_server_structure_dedupes_and_syncs_categories():
    server = {
        "id": "demo",
        "categories": ["Roadmap", "roadmap", " "],
        "channels": [
            {"id": "1", "name": "updates", "description": "Official notes", "category": "Roadmap"},
            {"id": "2", "name": "chat", "description": "General chat", "category": "Lounge"},
            {"id": "2", "name": "chat", "description": "Duplicate", "category": "Lounge"},
        ],
    }

    normalize_server_structure(server)

    assert server["categories"] == ["Roadmap", "Lounge"]
    assert server["channels"] == [
        {"id": "1", "name": "updates", "description": "Official notes", "category": "Roadmap"},
        {"id": "2", "name": "chat", "description": "General chat", "category": "Lounge"},
    ]


def test_parse_channel_lines_falls_back_for_malformed_or_unknown_category_syntax():
    parsed = parse_channel_lines("Unknown > alpha\nRoadmap >\nfoo>bar>baz", {}, ["Roadmap"])

    assert parsed == [
        {"id": parsed[0]["id"], "name": "Unknown > alpha", "description": "", "category": ""},
        {"id": parsed[1]["id"], "name": "Roadmap >", "description": "", "category": ""},
        {"id": parsed[2]["id"], "name": "foo>bar>baz", "description": "", "category": ""},
    ]
    assert all(channel["id"] for channel in parsed)
