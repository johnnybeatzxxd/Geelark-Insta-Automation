import time
import random
import re
from rich import print as rprint
from database import get_pending_batch, update_target_status
from nav_search import open_search_page, search_for_user, get_follow_status, click_follow
from helper import open_page 
from warmup import perform_scroll, perform_double_tap 
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

log = rprint

# --- CONSTANTS ---
ID_TAB_BAR = "com.instagram.android:id/tab_bar"
ID_GRID_IMAGE = "com.instagram.android:id/image_button"
# Post Count IDs (Try familiar first, then fallback)
ID_POST_COUNT_FAMILIAR = "com.instagram.android:id/profile_header_familiar_post_count_value"
ID_POST_COUNT_STD = "com.instagram.android:id/row_profile_header_textview_post_count"

# --- HELPER: NAVIGATION RECOVERY ---
def return_to_base_state(driver):
    """
     presses Back until the Bottom Tab Bar is visible.
    """
    log("[cyan]   * Nav: Returning to base state...[/cyan]")
    for i in range(5): 
        try:
            tabs = driver.find_elements(AppiumBy.ID, ID_TAB_BAR)
            if tabs and tabs[0].is_displayed():
                return True
            driver.back()
            time.sleep(1.5)
        except:
            driver.back()
            time.sleep(1)
    return False

def human_sleep(min_s, max_s):
    time.sleep(random.uniform(min_s, max_s))

def chance(percentage):
    return random.randint(1, 100) <= percentage

# --- VETTING LOGIC ---

def parse_count(text):
    """Converts '1,234', '10.5k', '1M' to integers."""
    if not text: return 0
    text = text.lower().strip().replace(',', '')
    multiplier = 1
    if 'k' in text:
        multiplier = 1000
        text = text.replace('k', '')
    elif 'm' in text:
        multiplier = 1000000
        text = text.replace('m', '')
    try:
        return int(float(text) * multiplier)
    except: return 0

def vet_profile_content(driver):
    """
    1. Checks post count >= 1.
    2. Opens 2 posts (if available).
    3. Likes them quickly.
    """
    try:
        # 1. Check Post Count
        count = 0
        candidates = driver.find_elements(AppiumBy.ID, ID_POST_COUNT_FAMILIAR)
        if not candidates:
            candidates = driver.find_elements(AppiumBy.ID, ID_POST_COUNT_STD)
        
        if candidates:
            count = parse_count(candidates[0].text)
            log(f"[dim]Profile has {count} posts.[/dim]")
            
            # CHANGED: Allow vetting if at least 1 post exists
            if count < 1:
                log("[dim]Profile empty. Skipping content check.[/dim]")
                return
        
        # 2. Find Grid Images
        images = driver.find_elements(AppiumBy.ID, ID_GRID_IMAGE)
        if not images:
            log("[yellow]No images found (Private?).[/yellow]")
            return

        # 3. Determine how many to like (Max 2, but don't crash if only 1 exists)
        posts_to_like = min(len(images), 2)
        
        # 4. Fast Loop
        for i in range(posts_to_like):
            log(f"[blue]   * Vetting: checking post {i+1}...[/blue]")
            
            # Re-find images in case the DOM got stale after backing out
            current_images = driver.find_elements(AppiumBy.ID, ID_GRID_IMAGE)
            if not current_images: break
            
            # Click the image (i ensures we pick different ones, e.g., 0 then 1)
            current_images[i].click()
            
            # Quick wait (Fast judgement)
            human_sleep(1.5, 2.5) 
            
            # 70% Chance to Like
            if chance(70):
                dims = driver.get_window_size()
                # Use the new coords-enabled double tap
                perform_double_tap(driver, coords=(dims['width']//2, dims['height']//2))
                human_sleep(0.5, 1.0) # Short pause after like

            # Back out
            driver.back()
            human_sleep(1.0, 1.5) # Quick animation wait

    except Exception as e:
        log(f"[red]Vetting Error: {e}[/red]")
        driver.back() # Emergency exit

def perform_follow_session(driver, config):
    # 1. Get Targets
    targets = get_pending_batch(config['batch_size'])
    if not targets:
        log("[yellow]No pending targets in Database.[/yellow]")
        return

    log(f"[bold green]Starting Follow Session. Targets: {len(targets)}[/bold green]")
    successful_follows = 0
    
    # 2. Main Loop
    for i, target in enumerate(targets):
        username = target.username
        log(f"\n[cyan]--- Processing {i+1}/{len(targets)}: {username} ---[/cyan]")

        # A. Pattern Break
        if i > 0 and i % config['pattern_break'] == 0:
            log("[bold magenta]Taking a Pattern Break...[/bold magenta]")
            return_to_base_state(driver)
            if open_page(driver, "Home"):
                human_sleep(20, 40) 
            log("[magenta]Break over. Returning to Search.[/magenta]")

        # B. Navigate
        return_to_base_state(driver)
        if not open_search_page(driver): break
        
        if not search_for_user(driver, username):
            log(f"[red]Could not find user {username}. Marking failed.[/red]")
            update_target_status(username, "failed")
            continue

        # C. Vetting (Scroll Profile + Open Post)
        log("[dim]Vetting profile layout...[/dim]")
        human_sleep(1, 2)
        perform_scroll(driver, direction="down", duration_ms=500)
        human_sleep(1, 2)
        
        # --- NEW: CONTENT VETTING ---
        if config.get('do_vetting', True):
            # Scroll back up to top to see grid clearly
            driver.swipe(360, 600, 360, 1200, 500) 
            human_sleep(1, 2)
            vet_profile_content(driver)
        # ----------------------------

        # Scroll back up to find Follow button if we drifted
        driver.swipe(360, 600, 360, 1200, 500) 
        human_sleep(1, 2)

        # D. Check Status & Follow
        status = get_follow_status(driver)
        
        if status == "can_follow":
            log(f"[green]User is valid. Following...[/green]")
            if click_follow(driver):
                update_target_status(username, "followed")
                successful_follows += 1
                delay = random.uniform(config['min_delay'], config['max_delay'])
                log(f"[dim]Sleeping for {delay:.1f}s...[/dim]")
                time.sleep(delay)
            else:
                log("[red]Failed to click button.[/red]")
            
        elif status == "already_following":
            log("[yellow]Already following. Skipping.[/yellow]")
            update_target_status(username, "already_followed")
            
        else:
            log(f"[yellow]Status '{status}'. Skipping.[/yellow]")
            update_target_status(username, "ignored")

    log(f"[bold green]Session Complete. Followed: {successful_follows}[/bold green]")
