import time
import random
from rich import print as rprint
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import browse_reels

# --- IMPORT THE RELIABLE NAVIGATOR ---
try:
    from helper import open_page
except ImportError:
    rprint("[red]CRITICAL: Could not import 'open_page' from 'helper.py'. Ensure file exists.[/red]")

log = rprint

# --- CONSTANTS ---
ID_TAB_BAR = "com.instagram.android:id/tab_bar" 

# Feed Media
ID_MEDIA_CONTAINER = "com.instagram.android:id/zoomable_view_container" 
ID_MEDIA_IMAGE_VIEW = "com.instagram.android:id/row_feed_photo_imageview" 
ID_CLIPS_CONTAINER = "com.instagram.android:id/clips_video_container" 

# Suggestions
ID_SUGGESTION_CAROUSEL = "com.instagram.android:id/similar_accounts_carousel_recycler_view"
ID_FOLLOW_BUTTON = "com.instagram.android:id/suggested_user_card_follow_button"

# Interaction
ID_LIKE_BUTTON = "com.instagram.android:id/row_feed_button_like" 

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

# --- NAVIGATION & AWARENESS ---

def is_comment_modal_open(driver):
    try:
        titles = driver.find_elements(AppiumBy.XPATH, "//*[@text='Comments']")
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

def is_in_reel_viewer(driver):
    """Verifies we are actually watching a Reel."""
    try:
        titles = driver.find_elements(AppiumBy.XPATH, "//android.widget.TextView[@text='Reels']")
        if titles and titles[0].is_displayed(): return True
        comments = driver.find_elements(AppiumBy.XPATH, "//*[@text='Add comment...']")
        if comments and comments[0].is_displayed(): return True
        return False
    except: return False

def ensure_back_to_feed(driver):
    """
    1. Soft Recovery: Press Back 3 times.
    2. Hard Recovery: If that fails, call open_page("HOME").
    """
    log("[cyan]   * Awareness: verifying return to Feed...[/cyan]")
    
    # PHASE 1: Soft Recovery (Back Button)
    for i in range(3):
        if is_on_home_feed(driver):
            log("[green]     -> Confirmed: Back on Home Feed.[/green]")
            return True
        
        log(f"[yellow]     -> Not on Feed (Attempt {i+1}). Pressing Back...[/yellow]")
        driver.back()
        human_sleep(1.5, 2.0)
    
    # Final check before Hard Recovery
    if is_on_home_feed(driver): return True

    # PHASE 2: Hard Recovery (Relaunch App)
    log("[bold red]     ! Soft recovery failed. Initiating HARD RECOVERY (open_page)...[/bold red]")
    try:
        # This will check if app is open, launch it if not, and click Home tab
        if open_page(driver, "HOME"):
            log("[bold green]     -> Hard Recovery Successful. We are back.[/bold green]")
            return True
    except Exception as e:
        log(f"[red]     -> Hard Recovery Failed: {e}[/red]")

    return False

# --- INTELLIGENCE ---

def get_center_post_media(driver):
    try:
        dims = driver.get_window_size()
        screen_center_y = dims['height'] / 2
        candidates = []
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_MEDIA_CONTAINER))
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_MEDIA_IMAGE_VIEW))
        candidates.extend(driver.find_elements(AppiumBy.ID, ID_CLIPS_CONTAINER))

        best_element = None
        min_dist = float('inf')

        for el in candidates:
            try:
                rect = el.rect
                el_center_y = rect['y'] + (rect['height'] / 2)
                dist = abs(screen_center_y - el_center_y)
                if dist < min_dist:
                    min_dist = dist
                    best_element = el
            except: continue
        return best_element
    except: return None

def is_sponsored_ad(element):
    try:
        desc = str(element.get_attribute("content-desc"))
        if "Sponsored" in desc:
            log(f"[yellow]     -> Detected AD: {desc[:25]}... -> SKIPPING[/yellow]")
            return True
        return False
    except: return False

# --- ACTIONS ---

def perform_scroll(driver, direction="down", duration_ms=None):
    if duration_ms is None: duration_ms = random.randint(400, 700)
    dims = driver.get_window_size()
    w, h = dims['width'], dims['height']
    cx = (w // 2) + random.randint(-20, 20)
    if direction == "down":
        driver.swipe(cx, int(h * 0.85), cx, int(h * 0.15), duration_ms)
    elif direction == "right":
        driver.swipe(int(w * 0.85), int(h * 0.6), int(w * 0.15), int(h * 0.6), duration_ms)

def perform_double_tap(driver, element=None, coords=None):
    try:
        actions = ActionChains(driver)
        if element:
            rect = element.rect
            cx, cy = rect['x'] + (rect['width'] // 2), rect['y'] + (rect['height'] // 2)
            actions.w3c_actions.pointer_action.move_to_location(cx, cy)
        elif coords:
            actions.w3c_actions.pointer_action.move_to_location(coords[0], coords[1])
        else: return False

        actions.w3c_actions.pointer_action.pointer_down().pause(0.1).pointer_up()
        actions.w3c_actions.pointer_action.pause(0.1)
        actions.w3c_actions.pointer_action.pointer_down().pause(0.1).pointer_up()
        actions.perform()
        log("[magenta]   * Action: Double-tapped (Like).[/magenta]")
        return True
    except: return False

def action_open_post_image(driver):
    try:
        target_media = get_center_post_media(driver)
        if not target_media or is_sponsored_ad(target_media): return

        log("[bold cyan]   * Action: Clicking Media...[/bold cyan]")
        target_media.click()
        human_sleep(2.5, 3.5)

        if is_in_reel_viewer(driver):
            watch_time = random.uniform(4.0, 12.0)
            log(f"[blue]     -> Reel Verified. Watching for {watch_time:.1f}s...[/blue]")
            time.sleep(watch_time)

            if watch_time > 9.0 and chance(80):
                log("[bold magenta]     -> Liked Reel![/bold magenta]")
                dims = driver.get_window_size()
                perform_double_tap(driver, coords=(dims['width']//2, dims['height']//2))
                time.sleep(1.0)
            
            ensure_back_to_feed(driver)

        elif is_on_home_feed(driver):
            log("[dim]     -> Static Image (Tags toggled).[/dim]")
            
        else:
            log("[bold red]     -> Unknown Page (Likely Ad Link). Bailing out![/bold red]")
            ensure_back_to_feed(driver)

    except Exception as e:
        log(f"[yellow]Open error: {e}[/yellow]")
        ensure_back_to_feed(driver)

def action_like_post(driver):
    try:
        target = get_center_post_media(driver)
        if target and not is_sponsored_ad(target):
            return perform_double_tap(driver, element=target)
    except: pass
    return False

def interact_with_suggestions_if_present(driver, follows_limit, current_follows):
    try:
        carousel = driver.find_elements(AppiumBy.ID, ID_SUGGESTION_CAROUSEL)
        if not carousel or not carousel[0].is_displayed(): return current_follows

        log("[cyan]INFO: Suggestion Carousel detected.[/cyan]")
        if chance(35):
            for _ in range(random.randint(1, 3)):
                perform_scroll(driver, direction="right")
                human_sleep(1.0, 2.0)
            
            if current_follows < follows_limit and chance(10):
                btns = carousel[0].find_elements(AppiumBy.ID, ID_FOLLOW_BUTTON)
                if btns:
                    random.choice(btns[:2]).click()
                    log("[bold magenta]   * Action: Followed suggested user.[/bold magenta]")
                    human_sleep(2.0, 3.0)
                    return current_follows + 1
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
        # Determine exact number of scrolls for this session
        target_scrolls = random.randint(feed_conf['min_scrolls'], feed_conf['max_scrolls'])
        
        log(f"[cyan]--- Phase 1: Feed ({target_scrolls} scrolls) ---[/cyan]")
        
        for i in range(target_scrolls):
            log(f"[dim]Feed Post {i+1}/{target_scrolls}[/dim]")
            # Safety Check
            if not is_on_home_feed(driver):
                log("[red]! Lost Navigation. Recovering...[/red]")
                if not ensure_back_to_feed(driver): return

            # Look at post (Speed affects this)
            human_sleep(1.5, 4.0, speed)
            
            # Suggestions Logic
            # We treat 'follows' as a hard limit from the config
            interact_with_suggestions_if_present(driver, limits['max_follows'], stats['follows'])

            # Like Logic
            if chance(chances['like']):
                if stats["likes"] < limits['max_likes']:
                    if action_like_post(driver):
                        stats["likes"] += 1
                        human_sleep(0.5, 1.5, speed)
            
            # Scroll
            perform_scroll(driver, direction="down")
            
    else:
        log("[dim]Skipping Feed (Disabled in config)[/dim]")

    # ============================
    # PHASE 2: REELS SESSION
    # ============================
    if reels_conf['enabled']:
        # Determine duration
        target_minutes = random.randint(reels_conf['min_minutes'], reels_conf['max_minutes'])
        
        if target_minutes > 0:
            log(f"[cyan]--- Phase 2: Switching to Reels ({target_minutes} mins) ---[/cyan]")
            
            # Pass the constraints to the reels module
            # You might need to update browse_reels_session to accept speed/limits too
            browse_reels.browse_reels_session(
                driver, 
                duration_minutes=target_minutes
            )
    else:
        log("[dim]Skipping Reels (Disabled in config)[/dim]")

    log(f"[bold green]Session Complete. Stats: {stats}[/bold green]")
