# warmup_config.py

def get_day_config(day_number):
    """
    Returns the specific configuration dictionary for a given day (1-7).
    """
    
    configs = {
        1: {
            "label": "Day 1 - The Ghost",
            "feed": {"enabled": True, "min_scrolls": 13, "max_scrolls": 20},
            "reels": {"enabled": True, "min_minutes": 3, "max_minutes": 6},
            "limits": {"max_likes": 3, "max_follows": 2},
            "speed": "slow", # slow, normal, fast
            "chance": {"follow":30,"like": 20, "comment": 20, "xml_dump": 0}
        },
        2: {
            "label": "Day 2 - The Observer",
            "feed": {"enabled": True, "min_scrolls": 18, "max_scrolls": 25},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 8},
            "limits": {"max_likes": 5, "max_follows": 3},
            "speed": "slow",
            "chance": {"follow": 20,"like": 30, "comment": 20, "xml_dump": 0}
        },
        3: {
            "label": "Day 3 - Waking Up",
            "feed": {"enabled": True, "min_scrolls": 25, "max_scrolls": 30},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 10},
            "limits": {"max_likes": 10, "max_follows": 5},
            "speed": "normal",
            "chance": {"follow": 20,"like": 30, "comment": 30, "xml_dump": 0}
        },
        4: {
            "label": "Day 4 - Casual User",
            "feed": {"enabled": True, "min_scrolls": 45, "max_scrolls": 50},
            "reels": {"enabled": True, "min_minutes": 10, "max_minutes": 15},
            "limits": {"max_likes": 15, "max_follows": 8},
            "speed": "normal",
            "chance": {"follow": 20,"like": 30, "comment": 30, "xml_dump": 0}
        },
        5: {
            "label": "Day 5 - Active User",
            "feed": {"enabled": True, "min_scrolls": 45, "max_scrolls": 55},
            "reels": {"enabled": True, "min_minutes": 15, "max_minutes": 20},
            "limits": {"max_likes": 30, "max_follows": 8},
            "speed": "normal",
            "chance": {"follow":20,"like": 25, "comment": 30, "xml_dump": 0}
        },
        6: {
            "label": "Day 6 - The Addict",
            "feed": {"enabled": True, "min_scrolls": 50, "max_scrolls": 60},
            "reels": {"enabled": True, "min_minutes": 15, "max_minutes": 26},
            "limits": {"max_likes": 30, "max_follows": 10},
            "speed": "fast",
            "chance": {"follow":20,"like": 35, "comment": 30, "xml_dump": 0}
        },
        7: {
            "label": "Day 7 - Full Power",
            "feed": {"enabled": True, "min_scrolls": 55, "max_scrolls": 65},
            "reels": {"enabled": True, "min_minutes": 15, "max_minutes": 25},
            "limits": {"max_likes": 30, "max_follows": 12},
            "speed": "fast",
            "chance": {"follow":40,"like": 40, "comment": 35, "xml_dump": 0}
        },
    }
    return configs.get(day_number, configs[1]) # Default to Day 1 if invalid
