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
            "limits": {"max_likes": 3, "max_follows": 0},
            "speed": "slow", # slow, normal, fast
            "chance": {"like": 3, "comment": 0, "xml_dump": 10}
        },
        2: {
            "label": "Day 2 - The Observer",
            "feed": {"enabled": True, "min_scrolls": 5, "max_scrolls": 8},
            "reels": {"enabled": True, "min_minutes": 1, "max_minutes": 3},
            "limits": {"max_likes": 1, "max_follows": 0},
            "speed": "slow",
            "chance": {"like": 15, "comment": 0, "xml_dump": 10}
        },
        3: {
            "label": "Day 3 - Waking Up",
            "feed": {"enabled": True, "min_scrolls": 8, "max_scrolls": 12},
            "reels": {"enabled": True, "min_minutes": 3, "max_minutes": 5},
            "limits": {"max_likes": 2, "max_follows": 0},
            "speed": "normal",
            "chance": {"like": 20, "comment": 10, "xml_dump": 10}
        },
        4: {
            "label": "Day 4 - Casual User",
            "feed": {"enabled": True, "min_scrolls": 10, "max_scrolls": 15},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 8},
            "limits": {"max_likes": 3, "max_follows": 1},
            "speed": "normal",
            "chance": {"like": 25, "comment": 15, "xml_dump": 10}
        },
        5: {
            "label": "Day 5 - Active User",
            "feed": {"enabled": True, "min_scrolls": 15, "max_scrolls": 20},
            "reels": {"enabled": True, "min_minutes": 8, "max_minutes": 12},
            "limits": {"max_likes": 5, "max_follows": 1},
            "speed": "normal",
            "chance": {"like": 30, "comment": 20, "xml_dump": 10}
        },
        6: {
            "label": "Day 6 - The Addict",
            "feed": {"enabled": True, "min_scrolls": 20, "max_scrolls": 30},
            "reels": {"enabled": True, "min_minutes": 10, "max_minutes": 15},
            "limits": {"max_likes": 7, "max_follows": 2},
            "speed": "fast",
            "chance": {"like": 35, "comment": 20, "xml_dump": 5}
        },
        7: {
            "label": "Day 7 - Full Power",
            "feed": {"enabled": True, "min_scrolls": 25, "max_scrolls": 40},
            "reels": {"enabled": True, "min_minutes": 15, "max_minutes": 25},
            "limits": {"max_likes": 10, "max_follows": 3},
            "speed": "fast",
            "chance": {"like": 40, "comment": 25, "xml_dump": 5}
        }
    }
    
    return configs.get(day_number, configs[1]) # Default to Day 1 if invalid
