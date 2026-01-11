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
            "chance": {"like": 20, "comment": 20, "xml_dump": 0}
        },
        2: {
            "label": "Day 2 - The Observer",
            "feed": {"enabled": True, "min_scrolls": 18, "max_scrolls": 25},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 8},
            "limits": {"max_likes": 5, "max_follows": 1},
            "speed": "slow",
            "chance": {"like": 30, "comment": 20, "xml_dump": 0}
        },
        3: {
            "label": "Day 3 - Waking Up",
            "feed": {"enabled": True, "min_scrolls": 25, "max_scrolls": 30},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 10},
            "limits": {"max_likes": 10, "max_follows": 4},
            "speed": "normal",
            "chance": {"like": 30, "comment": 30, "xml_dump": 0}
        },
        4: {
            "label": "Day 4 - Casual User",
            "feed": {"enabled": True, "min_scrolls": 10, "max_scrolls": 15},
            "reels": {"enabled": True, "min_minutes": 5, "max_minutes": 8},
            "limits": {"max_likes": 3, "max_follows": 1},
            "speed": "normal",
            "chance": {"like": 30, "comment": 30, "xml_dump": 0}
        },
        5: {
            "label": "Day 5 - Active User",
            "feed": {"enabled": True, "min_scrolls": 15, "max_scrolls": 20},
            "reels": {"enabled": True, "min_minutes": 8, "max_minutes": 12},
            "limits": {"max_likes": 5, "max_follows": 1},
            "speed": "normal",
            "chance": {"like": 30, "comment": 30, "xml_dump": 0}
        },
        6: {
            "label": "Day 6 - The Addict",
            "feed": {"enabled": True, "min_scrolls": 20, "max_scrolls": 30},
            "reels": {"enabled": True, "min_minutes": 10, "max_minutes": 15},
            "limits": {"max_likes": 10, "max_follows": 2},
            "speed": "fast",
            "chance": {"like": 35, "comment": 30, "xml_dump": 0}
        },
        7: {
            "label": "Day 7 - Full Power",
            "feed": {"enabled": True, "min_scrolls": 45, "max_scrolls": 60},
            "reels": {"enabled": True, "min_minutes": 15, "max_minutes": 25},
            "limits": {"max_likes": 20, "max_follows": 3},
            "speed": "fast",
            "chance": {"like": 40, "comment": 35, "xml_dump": 0}
        }
    }
    
    return configs.get(day_number, configs[1]) # Default to Day 1 if invalid
