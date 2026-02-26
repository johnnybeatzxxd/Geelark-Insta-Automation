import time
import random
import os
from rich import print as rprint

# Import the reels module (Note: You must convert this file to U2 as well!)
import browse_reels

# Default logger
log = rprint

# --- CONSTANTS ---
# Core Navigation
ID_TAB_BAR = "com.instagram.android:id/tab_bar"

# Comment / Modal Specifics
ID_BOTTOM_SHEET = "com.instagram.android:id/bottom_sheet_container"
ID_COMMENT_INPUT = "com.instagram.android:id/layout_comment_thread_edittext"

# Suggestions (Horizontal Carousel)
ID_SUGGESTION_CAROUSEL = (
    "com.instagram.android:id/similar_accounts_carousel_recycler_view"
)
ID_SUGGESTION_FOLLOW_BUTTON = (
    "com.instagram.android:id/suggested_user_card_follow_button"
)

# Feed Items (Vertical Scroll)
ID_MEDIA_CONTAINER = "com.instagram.android:id/zoomable_view_container"
ID_MEDIA_IMAGE_VIEW = "com.instagram.android:id/row_feed_photo_imageview"
ID_CLIPS_CONTAINER = "com.instagram.android:id/clips_video_container"

# Interaction Buttons
ID_LIKE_BUTTON = "com.instagram.android:id/row_feed_button_like"
ID_COMMENT_BUTTON = "com.instagram.android:id/row_feed_button_comment"
ID_INLINE_FOLLOW_BUTTON = "com.instagram.android:id/inline_follow_button"

# --- HELPERS ---


def chance(percentage: int) -> bool:
    return random.randint(1, 100) <= percentage


def human_sleep(min_seconds=1.0, max_seconds=3.0, speed_mode="normal"):
    """
    Sleeps based on speed multiplier.
    """
    multipliers = {"slow": 1.5, "normal": 1.0, "fast": 0.7}
    factor = multipliers.get(speed_mode, 1.0)

    duration = random.uniform(min_seconds, max_seconds) * factor
    time.sleep(duration)


def action_share_post(driver, share_targets=None):
    """
    Shares post via DM (specific user) or Copy Link.
    Includes robust 'Back' logic to return to feed.
    """
    try:
        # 1. Find Share Button
        share_btn = driver(description="Send post")
        if not share_btn.exists:
            share_btn = driver(resourceId="com.instagram.android:id/button_send")

        if not share_btn.exists:
            log("[dim]Share button not found. Skipping.[/dim]")
            return False

        log("[blue]   * Action: Clicking Share...[/blue]")
        share_btn.click()
        time.sleep(1.5)

        # 2. Setup Target
        target_user = None
        if share_targets and len(share_targets) > 0:
            target_user = random.choice(share_targets)

        # --- PATH A: DM SHARE ---
        if target_user:
            log(f"[cyan]     -> Sharing to DM: {target_user}[/cyan]")

            # A1. Find Search Box
            search_box = driver(resourceId="com.instagram.android:id/search_edit_text")
            if not search_box.exists:
                log("[red]Search box missing in share sheet.[/red]")
                return False  # Finally block will handle backing out

            # A2. Type User
            search_box.click()
            time.sleep(0.5)
            search_box.set_text(target_user)
            time.sleep(2.5)  # Wait for results

            # A3. Find Result (Robust Strategy)
            # Strategy 1: Look for exact handle match in secondary text (the username)
            user_row = driver(
                resourceId="com.instagram.android:id/row_user_secondary_name",
                text=target_user,
            )

            # Strategy 2: Look for partial match in primary text (display name)
            if not user_row.exists:
                user_row = driver(
                    resourceId="com.instagram.android:id/row_user_primary_name",
                    textContains=target_user,
                )

            # Strategy 3: Just pick the first result if we are confident (Optional, keeping it safe for now)

            if user_row.exists:
                user_row.click()
                log(f"[green]     -> Selected user: {target_user}[/green]")
                time.sleep(1)

                # A4. Click Send
                # The "Send" button appears at the bottom after selection
                send_btn = driver(text="Send")
                if not send_btn.exists:
                    send_btn = driver(
                        resourceId="com.instagram.android:id/direct_send_button"
                    )

                if send_btn.exists:
                    send_btn.click()
                    log("[bold green]     -> SENT![/bold green]")
                    return True
                else:
                    log("[yellow]Send button did not appear.[/yellow]")
            else:
                log(f"[yellow]User '{target_user}' not found in results.[/yellow]")

        # --- PATH B: COPY LINK ---
        else:
            log("[cyan]     -> Action: Copy Link[/cyan]")
            # U2 Selector for "Copy link" text
            copy_btn = driver(text="Copy link")
            if copy_btn.exists:
                copy_btn.click()
                log("[green]     -> Link Copied.[/green]")
                # Usually copying link closes the menu automatically, but we check in finally
                return True
            else:
                log("[yellow]Copy link button not found.[/yellow]")

        return False

    except Exception as e:
        log(f"[red]Share action failed: {e}[/red]")
        return False

    finally:
        # --- CRITICAL: RETURN TO FEED ---
        # Keep pressing back until we see the Tab Bar (Home Feed)
        # Max 3 tries to avoid infinite loops
        for _ in range(3):
            if driver(resourceId=ID_TAB_BAR).exists:
                break
            # Check if we are still on search input (Keyboard might be up)
            driver.press("back")
            time.sleep(1)


def is_ad_or_suggestion(element_info):
    """
    Checks if an element is an Ad based on content-desc.
    Args:
        element_info: The dictionary returned by u2 element.info
    """
    try:
        desc = element_info.get("contentDescription")
        if not desc:
            return False

        desc_str = str(desc)
        if "Sponsored" in desc_str:
            log(
                f"[yellow]     -> Detected AD: '{desc_str[:25]}...' -> SKIPPING[/yellow]"
            )
            return True
        return False
    except:
        return False


# --- NAVIGATION & AWARENESS ---


def is_comment_modal_open(driver):
    try:
        # U2 Check: Exists and is enabled/visible
        if driver(resourceId=ID_COMMENT_INPUT).exists:
            return True

        # Check title text
        if driver(
            text="Comments", resourceId="com.instagram.android:id/title_text_view"
        ).exists:
            return True

        return False
    except:
        return False


def is_on_home_feed(driver):
    """Checks if we are safely on the home feed."""
    try:
        # Check if Tab Bar exists
        if not driver(resourceId=ID_TAB_BAR).exists:
            return False
        if is_comment_modal_open(driver):
            return False
        return True
    except:
        return False


def ensure_back_to_feed(driver):
    """Smart Backing: Loops until free of modals/keyboards."""
    log("[cyan]   * Awareness: verifying return to Feed...[/cyan]")
    max_retries = 4

    for attempt in range(max_retries):
        if is_on_home_feed(driver):
            log("[green]     -> Confirmed: Back on Home Feed.[/green]")
            return True

        if is_comment_modal_open(driver):
            log(f"[yellow]     -> Comment Modal detected. Pressing Back...[/yellow]")
        else:
            log(
                f"[yellow]     -> Not on feed (Unknown state). Pressing Back...[/yellow]"
            )

        driver.press("back")
        human_sleep(1.5, 2.5)

    if is_on_home_feed(driver):
        return True
    log("[red]CRITICAL: Stuck. Unable to return to Feed.[/red]")
    return False


# --- ACTIONS ---


def perform_double_tap(driver, element=None, coords=None):
    """
    Performs a double tap.
    Args:
        driver: U2 Device Object
        element: U2 UiObject
        coords: Tuple (x, y)
    """
    try:
        x, y = 0, 0

        if element:
            # U2 element.center() returns (x, y)
            x, y = element.center()
        elif coords:
            x, y = coords[0], coords[1]
        else:
            log("[red]Double Tap Error: No element or coords provided.[/red]")
            return False

        # U2 has native double click support which is very reliable
        driver.double_click(x, y)

        log("[magenta]   * Action: Double-tapped.[/magenta]")
        return True
    except Exception as e:
        log(f"[red]Error double tapping: {e}[/red]")
        return False


def perform_scroll(driver, direction="down", speed="normal"):
    """
    Robust, straight-line scrolling. Matches Appium behavior.
    """
    w, h = driver.window_size()

    # 1. Dead Center X-Axis (Stable)
    cx = w * 0.5

    # 2. Logic
    start_y = 0
    end_y = 0
    duration = 0.5

    if direction == "down":
        # SCROLL DOWN = Finger moves BOTTOM -> TOP
        # Start: 85% down the screen
        # End: 10% from the top
        # Delta: 75% of screen height (Long scroll)
        start_y = h * 0.85
        end_y = h * 0.10

        if speed == "fast":
            duration = 0.1
        elif speed == "slow":
            duration = 0.45
        else:
            duration = 0.25

        driver.swipe(cx, start_y, cx, end_y, duration)

    elif direction == "up":
        # SCROLL UP = Finger moves TOP -> BOTTOM
        start_y = h * 0.20
        end_y = h * 0.90
        driver.swipe(cx, start_y, cx, end_y, 0.3)

    elif direction == "right":
        # Carousel Swipe = RIGHT -> LEFT
        start_x = w * 0.90
        end_x = w * 0.10
        cy = h * 0.5  # Center Y
        driver.swipe(start_x, cy, end_x, cy, 0.3)


def action_open_and_dump_xml(driver):
    """
    Finds a VALID, NON-AD post, clicks it, waits 10s, dumps XML.
    """
    try:
        # U2 Selector Strategy: Find elements that match ANY of these IDs
        # We loop through candidates.
        # Note: Iterating U2 lists can be slower than Appium if many elements exist.

        target_element = None

        # We define a list of IDs to check
        candidate_ids = [ID_MEDIA_CONTAINER, ID_MEDIA_IMAGE_VIEW, ID_CLIPS_CONTAINER]

        for res_id in candidate_ids:
            # Get all elements matching this ID
            elems = driver(resourceId=res_id)
            count = elems.count

            for i in range(count):
                try:
                    el = elems[i]
                    info = el.info
                    # Check visibility (bounds > 0) and Ad status
                    bounds = info.get("bounds")
                    if bounds and not is_ad_or_suggestion(info):
                        target_element = el
                        break
                except:
                    continue

            if target_element:
                break

        if not target_element:
            return

        log("[bold cyan]   * DATA COLLECTION: Clicking Post...[/bold cyan]")
        target_element.click()

        # Wait slightly
        time.sleep(2)

        try:
            # U2 dump_hierarchy is equivalent to page_source
            xml_content = driver.dump_hierarchy()
            with open("posts.xml", "w", encoding="utf-8") as f:
                f.write(xml_content)
            log(f"[bold green]     -> XML saved.[/bold green]")
        except:
            pass

        if not ensure_back_to_feed(driver):
            raise Exception("Stuck after dumping XML")

    except Exception as e:
        log(f"[yellow]Dump error: {e}[/yellow]")
        driver.press("back")


def action_like_post(driver):
    """Like a visible post (skipping ads)."""
    try:
        # Search priority: Media Container -> Image -> Clips
        candidate_ids = [ID_MEDIA_CONTAINER, ID_MEDIA_IMAGE_VIEW, ID_CLIPS_CONTAINER]

        for res_id in candidate_ids:
            elems = driver(resourceId=res_id)
            if elems.exists:
                # We usually interact with the first visible one
                for i in range(min(2, elems.count)):  # Check top 2 to find non-ad
                    el = elems[i]
                    if not is_ad_or_suggestion(el.info):
                        return perform_double_tap(driver, el)
    except:
        pass
    return False


def action_follow_from_feed(driver):
    """
    Finds a visible 'Follow' button on a feed post and clicks it.
    """
    try:
        # Find all inline buttons
        follow_btns = driver(resourceId=ID_INLINE_FOLLOW_BUTTON)

        if not follow_btns.exists:
            return False

        # Iterate to find one that explicitly says "Follow"
        # U2 .get_text() extracts the text
        for i in range(follow_btns.count):
            try:
                btn = follow_btns[i]
                text = btn.get_text()

                if text and text.strip() == "Follow":
                    log(
                        f"[bold magenta]   * Action: Clicking Follow on Feed Post...[/bold magenta]"
                    )
                    btn.click()
                    return True
            except:
                continue

    except Exception as e:
        log(f"[yellow]Follow action failed: {e}[/yellow]")

    return False


def interact_with_suggestions_if_present(driver, follows_limit, current_follows):
    """Horizontal scroll on suggestion carousel."""
    try:
        # Check existence
        if not driver(resourceId=ID_SUGGESTION_CAROUSEL).exists:
            return current_follows

        log("[cyan]INFO: Suggestion Carousel detected.[/cyan]")
        if chance(35):
            for _ in range(random.randint(1, 3)):
                perform_scroll(driver, direction="right")
                human_sleep(1.0, 2.0)

    except:
        pass
    return current_follows


# --- MAIN CONTROLLER ---


def perform_warmup(driver, config, logger_func=None, state=None):
    """
    Executes warmup based on the specific Day Configuration.
    Args:
        driver: UiAutomator2 Device Object
    """
    global log
    if logger_func:
        log = logger_func

    if state is None:
        state = {"phase": "feed", "current_scroll": 0, "target_scrolls": None}

    log(
        f"[bold green]Starting Warmup Routine: {config.get('label', 'Unknown Day')}[/bold green]"
    )

    # 1. Extract Configs (Safe extraction)
    feed_conf = config.get("feed", {})
    reels_conf = config.get("reels", {})
    limits = config.get("limits", {})
    chances = config.get("chance", {})
    speed = config.get("speed", "normal")
    share_list = config.get("share_targets", [])

    stats = {"likes": 0, "follows": 0, "opened": 0}

    # ============================
    # PHASE 1: HOME FEED BROWSING
    # ============================
    if feed_conf.get("enabled", False):
        min_s = feed_conf.get("minScrolls", 10)
        max_s = feed_conf.get("maxScrolls", 20)
        target_scrolls = random.randint(min_s, max_s)

        log(f"[cyan]--- Phase 1: Feed ({target_scrolls} scrolls) ---[/cyan]")

        for i in range(state["current_scroll"], target_scrolls):
            log(f"[dim]Feed Post {i + 1}/{target_scrolls}[/dim]")

            # Safety Check
            if not is_on_home_feed(driver):
                log("[red]! Lost Navigation. Recovering...[/red]")
                if not ensure_back_to_feed(driver):
                    return

            human_sleep(1.5, 4.0, speed)

            # 1. Suggestions (Horizontal)
            limit_follows = limits.get("maxFollows", 3)
            interact_with_suggestions_if_present(
                driver, limit_follows, stats["follows"]
            )

            # 3. DECISION: Like Feed Post
            if chance(chances.get("like", 1)):
                if stats["likes"] < limits.get("maxLikes", 5):
                    if action_like_post(driver):
                        stats["likes"] += 1
                        human_sleep(0.5, 1.5, speed)

            # 5. DECISION: Share Post (New)
            if chance(chances.get("share", 0)):
                if action_share_post(driver, share_targets=share_list):
                    stats["shares"] = stats.get("shares", 0) + 1
                    human_sleep(1.5, 3.0, speed)

            # Scroll...
            # 4. DECISION: Follow Feed Post
            if chance(chances.get("follow", 0)):
                if stats["follows"] < limits.get("maxFollows", 3):
                    if action_follow_from_feed(driver):
                        stats["follows"] += 1
                        human_sleep(1.0, 2.0, speed)

            # Scroll
            if speed == "fast":
                # 70% chance to flick fast
                current_action_speed = "fast" if chance(70) else "normal"
            else:
                # 70% chance to drag slow
                current_action_speed = "slow" if chance(70) else "normal"

            perform_scroll(driver, direction="down", speed=current_action_speed)
            state["current_scroll"] = i + 1

        state["phase"] = "reels"
    else:
        log("[dim]Skipping Feed (Disabled in config)[/dim]")

    # ============================
    # PHASE 2: REELS SESSION
    # ============================
    if reels_conf.get("enabled", False) and state["phase"] == "reels":
        min_m = reels_conf.get("minMinutes", 5)
        max_m = reels_conf.get("maxMinutes", 10)
        target_minutes = random.randint(min_m, max_m)

        if target_minutes > 0:
            log(
                f"[cyan]--- Phase 2: Switching to Reels ({target_minutes} mins) ---[/cyan]"
            )
            # browse_reels is also converted to U2!
            browse_reels.browse_reels_session(
                driver, duration_minutes=target_minutes, logger_func=log
            )
            state["phase"] = "complete"
    else:
        log("[dim]Skipping Reels (Disabled in config)[/dim]")

    log(f"[bold green]Session Complete. Stats: {stats}[/bold green]")
