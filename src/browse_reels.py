import time
import random
from rich import print as rprint

# Import helper for consistent logging/logic
try:
    from helper import open_page
except: pass

log = rprint

# --- CONSTANTS ---
ID_REELS_TAB = "com.instagram.android:id/clips_tab"
ID_LIKE_BUTTON = "com.instagram.android:id/like_button"
ID_COMMENT_BUTTON = "com.instagram.android:id/comment_button"

# --- HELPERS ---

def chance(percentage: int) -> bool:
    return random.randint(1, 100) <= percentage

def human_sleep(min_seconds=1.0, max_seconds=3.0):
    time.sleep(random.uniform(min_seconds, max_seconds))

def perform_double_tap_center(driver):
    """Likes the Reel by double-tapping the center."""
    try:
        w, h = driver.window_size()
        cx = w / 2
        cy = h / 2
        
        # U2 native double click
        driver.double_click(cx, cy)
        log("[magenta]   * Action: Double-tapped Reel (Like).[/magenta]")
    except Exception as e:
        log(f"[yellow]Double tap error: {e}[/yellow]")

def perform_swipe_up(driver):
    """Next Reel."""
    w, h = driver.window_size()
    cx = w / 2
    # Fast swipe UP (Bottom -> Top)
    driver.swipe(cx, int(h * 0.8), cx, int(h * 0.2), 0.1)

def perform_comment_scroll(driver):
    """Scrolls down inside the comments section."""
    w, h = driver.window_size()
    cx = w / 2
    # Smaller scroll for comments
    driver.swipe(cx, int(h * 0.7), cx, int(h * 0.4), 0.2)

# --- ACTIONS ---

def action_interact_with_comments(driver):
    """
    Opens comments, scrolls, maybe likes a comment, then closes.
    """
    try:
        # 1. Open Comments
        # U2: Find by Resource ID
        comment_btn = driver(resourceId=ID_COMMENT_BUTTON)
        
        if not comment_btn.exists: 
            return

        log("[blue]   * Action: Opening Reel Comments...[/blue]")
        comment_btn.click()
        human_sleep(2.0, 3.0)

        # 2. Scroll a bit (Read)
        scrolls = random.randint(1, 3)
        for _ in range(scrolls):
            perform_comment_scroll(driver)
            human_sleep(1.0, 2.5)

        # 3. Like a Comment (20% Chance)
        if chance(20):
            log("[dim]     -> Reading comments intensely...[/dim]")
            human_sleep(1.0, 2.0)

        # 4. Close Comments
        # Press Back (Reliable on U2)
        log("[blue]   * Action: Closing comments.[/blue]")
        driver.press("back")
        human_sleep(1.0, 1.5)

    except Exception as e:
        log(f"[yellow]Comment interaction failed: {e}[/yellow]")
        driver.press("back") # Rescue

def action_watch_reel(driver):
    """
    Simulates watching a single reel.
    """
    # 1. The "Hook" - Watch first 2-3 seconds
    human_sleep(2.0, 3.0)
    
    # 2. Boredom Check
    if chance(40):
        log("[dim]   -> Bored. Skipping.[/dim]")
        return 

    # 3. Watch Longer
    watch_time = random.uniform(4.0, 10.0)
    log(f"[dim]   -> Watching for {watch_time:.1f}s...[/dim]")
    time.sleep(watch_time)

    # 4. Interaction: Like
    if chance(35):
        perform_double_tap_center(driver)
        human_sleep(0.5, 1.0)

    # 5. Interaction: Comments
    if chance(40):
        action_interact_with_comments(driver)

# --- MAIN REELS CONTROLLER ---

def browse_reels_session(driver, duration_minutes=5, log_func=None):
    """
    Watches Reels for a specific duration.
    Args:
        driver: UiAutomator2 Device
    """
    if log_func:
        global log
        log = log_func
    log(f"[bold magenta]Starting Reels Session | Duration: ~{duration_minutes} mins[/bold magenta]")
    
    # 1. Switch to Reels Tab
    try:
        # Check if tab exists and click
        reels_tab = driver(resourceId=ID_REELS_TAB)
        if reels_tab.exists(timeout=10):
            reels_tab.click()
            log("[green]Switched to Reels Tab.[/green]")
            human_sleep(2.0, 3.0)
        else:
            log("[red]Reels tab not found.[/red]")
            return
    except Exception as e:
        log(f"[red]Error opening Reels tab: {e}[/red]")
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
