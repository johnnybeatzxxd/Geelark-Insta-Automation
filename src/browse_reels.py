import time
import random
from rich import print as rprint
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Import existing helpers if they are in a shared file, otherwise re-defined here for modularity
try:
    from helper import open_page
except: pass

log = rprint

# --- CONSTANTS ---
ID_REELS_TAB = "com.instagram.android:id/clips_tab"
ID_LIKE_BUTTON = "com.instagram.android:id/like_button"
ID_COMMENT_BUTTON = "com.instagram.android:id/comment_button"

# Comment Modal Constants
ID_COMMENT_HEART = "com.instagram.android:id/item_emoji" # Often the heart is an image view in the row
# Alternatively, check for resource-id="com.instagram.android:id/row_comment_like_button" if available later.
# Based on your previous Feed XML, comment likes were tricky. We will try a generic approach or tap coordinates.

# --- HELPERS ---

def chance(percentage: int) -> bool:
    return random.randint(1, 100) <= percentage

def human_sleep(min_seconds=1.0, max_seconds=3.0):
    time.sleep(random.uniform(min_seconds, max_seconds))

def perform_double_tap_center(driver):
    """Likes the Reel by double-tapping the center."""
    try:
        dims = driver.get_window_size()
        cx = dims['width'] // 2
        cy = dims['height'] // 2
        
        actions = ActionChains(driver)
        actions.w3c_actions.pointer_action.move_to_location(cx, cy)
        actions.w3c_actions.pointer_action.pointer_down().pause(0.08).pointer_up()
        actions.w3c_actions.pointer_action.pause(0.08)
        actions.w3c_actions.pointer_action.pointer_down().pause(0.08).pointer_up()
        actions.perform()
        log("[magenta]   * Action: Double-tapped Reel (Like).[/magenta]")
    except: pass

def perform_swipe_up(driver):
    """Next Reel."""
    dims = driver.get_window_size()
    w, h = dims['width'], dims['height']
    cx = w // 2
    # Fast swipe from bottom-ish to top-ish
    driver.swipe(cx, int(h * 0.8), cx, int(h * 0.2), 350)

def perform_comment_scroll(driver):
    """Scrolls down inside the comments section."""
    dims = driver.get_window_size()
    cx = dims['width'] // 2
    # Smaller scroll for comments
    driver.swipe(cx, int(dims['height']*0.7), cx, int(dims['height']*0.4), 800)

# --- ACTIONS ---

def action_interact_with_comments(driver):
    """
    Opens comments, scrolls, maybe likes a comment, then closes.
    """
    try:
        # 1. Open Comments
        comment_btns = driver.find_elements(AppiumBy.ID, ID_COMMENT_BUTTON)
        if not comment_btns: return

        log("[blue]   * Action: Opening Reel Comments...[/blue]")
        comment_btns[0].click()
        human_sleep(2.0, 3.0)

        # 2. Scroll a bit (Read)
        scrolls = random.randint(1, 3)
        for _ in range(scrolls):
            perform_comment_scroll(driver)
            human_sleep(1.0, 2.5)

        # 3. Like a Comment (20% Chance inside the comment section)
        if chance(20):
            # This logic is tricky without specific XML for the heart, 
            # but usually, we can find small ImageViews on the right side.
            # For now, we will just read to be safe.
            log("[dim]     -> Reading comments intensely...[/dim]")
            human_sleep(1.0, 2.0)

        # 4. Close Comments
        # Tap the top empty area to close the modal (Human way)
        # OR press Back (Safer way)
        log("[blue]   * Action: Closing comments.[/blue]")
        driver.back()
        human_sleep(1.0, 1.5)

    except Exception as e:
        log(f"[yellow]Comment interaction failed: {e}[/yellow]")
        driver.back() # Rescue

def action_watch_reel(driver):
    """
    Simulates watching a single reel.
    Logic:
    1. Wait (Attention span check).
    2. Maybe Like (35%).
    3. Maybe Open Comments (40%).
    4. Return to main loop.
    """
    # 1. The "Hook" - Watch first 2-3 seconds
    human_sleep(2.0, 3.0)
    
    # 2. Boredom Check
    # 40% of Reels are boring and we skip immediately
    if chance(40):
        log("[dim]   -> Bored. Skipping.[/dim]")
        return 

    # 3. Watch Longer (It's interesting)
    watch_time = random.uniform(4.0, 10.0)
    log(f"[dim]   -> Watching for {watch_time:.1f}s...[/dim]")
    time.sleep(watch_time)

    # 4. Interaction: Like
    if chance(35):
        perform_double_tap_center(driver)
        human_sleep(0.5, 1.0)

    # 5. Interaction: Comments (The 40% you asked for)
    if chance(40):
        action_interact_with_comments(driver)

# --- MAIN REELS CONTROLLER ---

def browse_reels_session(driver, duration_minutes=5):
    """
    Watches Reels for a specific duration.
    """
    log(f"[bold magenta]Starting Reels Session | Duration: ~{duration_minutes} mins[/bold magenta]")
    
    # 1. Switch to Reels Tab
    try:
        # Use your reliable open_page if available, else click ID
        # open_page(driver, "REELS") 
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((AppiumBy.ID, ID_REELS_TAB))
        )
        btn.click()
        log("[green]Switched to Reels Tab.[/green]")
        human_sleep(2.0, 3.0)
    except:
        log("[red]Failed to open Reels tab.[/red]")
        return

    # 2. The Loop
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    reel_count = 0

    while time.time() < end_time:
        reel_count += 1
        log(f"[magenta]--- Reel #{reel_count} ---[/magenta]")
        
        # Watch & Interact
        action_watch_reel(driver)
        
        # Next Reel
        perform_swipe_up(driver)
        
        # Tiny pause between swipes to let video load
        human_sleep(0.5, 1.0)

    log(f"[bold magenta]Reels Session Complete. Watched {reel_count} reels.[/bold magenta]")
    
    # Optional: Go back to Home Feed at the end to reset state
    # open_page(driver, "HOME")
