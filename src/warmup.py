import time
import random
import os
from rich import print as rprint
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Import the reels module
import browse_reels

log = rprint

# --- CONSTANTS ---
# Core Navigation
ID_TAB_BAR = "com.instagram.android:id/tab_bar" 

# Comment / Modal Specifics
ID_BOTTOM_SHEET = "com.instagram.android:id/bottom_sheet_container"
ID_COMMENT_INPUT = "com.instagram.android:id/layout_comment_thread_edittext" 

# Suggestions (Horizontal Carousel)
ID_SUGGESTION_CAROUSEL = "com.instagram.android:id/similar_accounts_carousel_recycler_view"
ID_SUGGESTION_FOLLOW_BUTTON = "com.instagram.android:id/suggested_user_card_follow_button"

# Feed Items (Vertical Scroll)
ID_MEDIA_CONTAINER = "com.instagram.android:id/zoomable_view_container" 
ID_MEDIA_IMAGE_VIEW = "com.instagram.android:id/row_feed_photo_imageview" 
ID_CLIPS_CONTAINER = "com.instagram.android:id/clips_video_container" 

# Interaction Buttons
ID_LIKE_BUTTON = "com.instagram.android:id/row_feed_button_like" 
ID_COMMENT_BUTTON = "com.instagram.android:id/row_feed_button_comment"
ID_INLINE_FOLLOW_BUTTON = "com.instagram.android:id/inline_follow_button" # The button next to username

# --- HELPERS ---

def chance(percentage: int) -> bool:
    return random.randint(1, 100) <= percentage

def human_sleep(min_seconds=1.0, max_seconds=3.0, speed_mode="normal"):
    """
    Sleeps based on speed multiplier.
    'slow' = 1.5x wait (Grandma mode)
    'normal' = 1.0x wait
    'fast' = 0.7x wait (Zoomer mode)
    """
    multipliers = {"slow": 1.5, "normal": 1.0, "fast": 0.7}
    factor = multipliers.get(speed_mode, 1.0)
    
    duration = random.uniform(min_seconds, max_seconds) * factor
    time.sleep(duration)

def is_ad_or_suggestion(element):
    """
    Checks if an element is an Ad based on content-desc.
    """
    try:
        desc = element.get_attribute("content-desc")
        if not desc: return False
        
        desc_str = str(desc)
        if "Sponsored" in desc_str:
            log(f"[yellow]     -> Detected AD: '{desc_str[:25]}...' -> SKIPPING[/yellow]")
            return True
        # Note: We don't skip "Suggested" here if you want to allow following suggested users,
        # but usually we want to interact with organic content. 
        # If you want to skip suggested posts too, uncomment next lines:
        # if "Suggested" in desc_str:
        #     return True
            
        return False
    except: return False

# --- NAVIGATION & AWARENESS ---

def is_comment_modal_open(driver):
    try:
        inputs = driver.find_elements(AppiumBy.ID, ID_COMMENT_INPUT)
        if inputs and inputs[0].is_displayed(): return True
        
        titles = driver.find_elements(AppiumBy.XPATH, "//*[@text='Comments' and @resource-id='com.instagram.android:id/title_text_view']")
        if titles and titles[0].is_displayed(): return True
        
        return False
    except: return False

def is_on_home_feed(driver):
    """Checks if we are safely on the home feed."""
    try:
        tabs = driver.find_elements(AppiumBy.ID, ID_TAB_BAR)
        if not tabs or not tabs[0].is_displayed(): return False
        if is_comment_modal_open(driver): return False
        return True
    except: return False

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
            log(f"[yellow]     -> Not on feed (Unknown state). Pressing Back...[/yellow]")
        
        driver.back()
        human_sleep(1.5, 2.5)

    if is_on_home_feed(driver): return True
    log("[red]CRITICAL: Stuck. Unable to return to Feed.[/red]")
    return False

# --- ACTIONS ---

def perform_double_tap(driver, element):
    try:
        rect = element.rect
        center_x = rect['x'] + (rect['width'] // 2)
        center_y = rect['y'] + (rect['height'] // 2)
        actions = ActionChains(driver)
        actions.w3c_actions.pointer_action.move_to_location(center_x, center_y)
        actions.w3c_actions.pointer_action.pointer_down().pause(0.1).pointer_up()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.pointer_down().pause(0.1).pointer_up()
        actions.perform()
        log("[magenta]   * Action: Double-tapped to like.[/magenta]")
        return True
    except: return False

def perform_scroll(driver, direction="down", duration_ms=None):
    if duration_ms is None: duration_ms = random.randint(400, 800)
    dims = driver.get_window_size()
    w, h = dims['width'], dims['height']
    cx = (w // 2) + random.randint(-20, 20)

    if direction == "down":
        driver.swipe(cx, int(h * 0.85), cx, int(h * 0.15), duration_ms)
    elif direction == "right":
        driver.swipe(int(w * 0.85), int(h * 0.6), int(w * 0.15), int(h * 0.6), duration_ms)

def action_open_and_dump_xml(driver):
    """
    Finds a VALID, NON-AD post, clicks it, waits 10s, dumps XML.
    """
    try:
        candidates = []
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_MEDIA_CONTAINER))
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_MEDIA_IMAGE_VIEW))
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_CLIPS_CONTAINER))

        target_element = None
        for element in candidates:
            try:
                if element.is_displayed() and not is_ad_or_suggestion(element):
                    target_element = element
                    break
            except: continue 

        if not target_element: return

        log("[bold cyan]   * DATA COLLECTION: Clicking Post...[/bold cyan]")
        target_element.click()
        
        # --- 10 SECOND WAIT FOR MANUAL CHECK ---
        # log("[bold yellow]   !!! SLEEPING 10 SECONDS (Manual Check) !!![/bold yellow]")
        # time.sleep(10)
        # ---------------------------------------

        try:
            source = driver.page_source
            with open("posts.xml", "w", encoding='utf-8') as f:
                f.write(source)
            log(f"[bold green]     -> XML saved.[/bold green]")
        except: pass
        
        if not ensure_back_to_feed(driver):
            raise TimeoutException("Stuck after dumping XML")

    except Exception as e:
        log(f"[yellow]Dump error: {e}[/yellow]")
        driver.back()

def action_like_post(driver):
    """Like a visible post (skipping ads)."""
    try:
        media_views = driver.find_elements(AppiumBy.ID, ID_MEDIA_CONTAINER)
        if not media_views: media_views = driver.find_elements(AppiumBy.ID, ID_MEDIA_IMAGE_VIEW)
        if not media_views: media_views = driver.find_elements(AppiumBy.ID, ID_CLIPS_CONTAINER)

        if media_views: 
            target = media_views[0]
            if target.is_displayed() and not is_ad_or_suggestion(target):
                return perform_double_tap(driver, target)
    except: pass
    return False

def action_follow_from_feed(driver):
    """
    Finds a visible 'Follow' button on a feed post and clicks it.
    """
    try:
        # Find all inline buttons currently loaded
        follow_btns = driver.find_elements(AppiumBy.ID, ID_INLINE_FOLLOW_BUTTON)
        
        target_btn = None
        
        # Filter for a valid, visible button that actually says "Follow"
        # This avoids clicking "Following" or "Requested"
        for btn in follow_btns:
            try:
                if btn.is_displayed() and btn.text == "Follow":
                    target_btn = btn
                    break 
            except: continue

        if target_btn:
            log(f"[bold magenta]   * Action: Clicking Follow on Feed Post...[/bold magenta]")
            target_btn.click()
            # Wait for button state change
            return True
            
    except Exception as e:
        log(f"[yellow]Follow action failed: {e}[/yellow]")
    
    return False

def interact_with_suggestions_if_present(driver, follows_limit, current_follows):
    """Horizontal scroll on suggestion carousel."""
    try:
        carousel = driver.find_elements(AppiumBy.ID, ID_SUGGESTION_CAROUSEL)
        if not carousel or not carousel[0].is_displayed(): return current_follows

        log("[cyan]INFO: Suggestion Carousel detected.[/cyan]")
        if chance(35):
            for _ in range(random.randint(1, 3)):
                perform_scroll(driver, direction="right")
                human_sleep(1.0, 2.0)
            
            # Note: We use a different ID for carousel follow buttons if needed
            # For now assuming same logic or skipping explicit carousel follows here 
            # since main loop handles feed follows.
    except: pass
    return current_follows

# --- MAIN CONTROLLER ---

def perform_warmup(driver, config):
    """
    Executes warmup based on the specific Day Configuration.
    """
    log(f"[bold green]Starting Warmup Routine: {config['label']}[/bold green]")
    
    # 1. Extract Configs
    feed_conf = config['feed']
    reels_conf = config['reels']
    limits = config['limits']
    chances = config['chance']
    speed = config['speed']
    
    stats = {"likes": 0, "follows": 0, "opened": 0}

    # ============================
    # PHASE 1: HOME FEED BROWSING
    # ============================
    if feed_conf['enabled']:
        target_scrolls = random.randint(feed_conf['min_scrolls'], feed_conf['max_scrolls'])
        log(f"[cyan]--- Phase 1: Feed ({target_scrolls} scrolls) ---[/cyan]")
        
        for i in range(target_scrolls):
            log(f"[dim]Feed Post {i+1}/{target_scrolls}[/dim]")
            
            # Safety Check
            if not is_on_home_feed(driver):
                log("[red]! Lost Navigation. Recovering...[/red]")
                if not ensure_back_to_feed(driver): return

            human_sleep(1.5, 4.0, speed)
            
            # 1. Suggestions (Horizontal)
            interact_with_suggestions_if_present(driver, limits['max_follows'], stats['follows'])

            # 2. DECISION: XML Dump (Debugging)
            if chance(chances.get('xml_dump', 0)):
                action_open_and_dump_xml(driver)
                stats['opened'] += 1
                perform_scroll(driver, direction="down")
                continue

            # 3. DECISION: Like Feed Post
            if chance(chances.get('like', 0)):
                if stats["likes"] < limits['max_likes']:
                    if action_like_post(driver):
                        stats["likes"] += 1
                        human_sleep(0.5, 1.5, speed)

            # 4. DECISION: Follow Feed Post (Vertical List)
            if chance(chances.get('follow', 0)):
                if stats["follows"] < limits['max_follows']:
                    if action_follow_from_feed(driver):
                        stats["follows"] += 1
                        human_sleep(1.0, 2.0, speed)
            
            # Scroll
            perform_scroll(driver, direction="down")
            
    else:
        log("[dim]Skipping Feed (Disabled in config)[/dim]")

    # ============================
    # PHASE 2: REELS SESSION
    # ============================
    if reels_conf['enabled']:
        target_minutes = random.randint(reels_conf['min_minutes'], reels_conf['max_minutes'])
        
        if target_minutes > 0:
            log(f"[cyan]--- Phase 2: Switching to Reels ({target_minutes} mins) ---[/cyan]")
            browse_reels.browse_reels_session(driver, duration_minutes=target_minutes)
    else:
        log("[dim]Skipping Reels (Disabled in config)[/dim]")

    log(f"[bold green]Session Complete. Stats: {stats}[/bold green]")
