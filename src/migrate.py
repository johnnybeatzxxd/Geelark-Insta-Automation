import json
from database import SystemConfig, db, DEFAULT_WARMUP_STRATEGY

def patch_db_config():
    print("Patching DB Config for Share feature...")
    
    try:
        conf = SystemConfig.get_or_none(SystemConfig.key == 'session_config')
        if not conf:
            print("No config found. Nothing to patch.")
            return

        current_data = json.loads(conf.value)
        
        # 1. Add share_targets to root if missing
        if "share_targets" not in current_data:
            current_data["share_targets"] = []
            print("Added 'share_targets' list.")

        # 2. Add 'share' chance to every day in warmup_strategy
        if "warmup_strategy" in current_data:
            strategy = current_data["warmup_strategy"]
            for day, settings in strategy.items():
                if "chance" in settings:
                    if "share" not in settings["chance"]:
                        # Use default from code, or 0
                        default_share = DEFAULT_WARMUP_STRATEGY.get(day, {}).get("chance", {}).get("share", 0)
                        settings["chance"]["share"] = default_share
                        print(f"Patched Day {day} share chance to {default_share}%")
        
        # 3. Save back to DB
        conf.value = json.dumps(current_data)
        conf.save()
        print("Configuration successfully patched.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    patch_db_config()
