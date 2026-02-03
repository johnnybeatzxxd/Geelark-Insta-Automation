import time
import random
from rich import print as rprint

# Import U2-converted helpers
# Note: You need to make sure nav_search.py is also converted (search_for_user, click_follow)
# Assuming you updated them, or we define them here if needed.
from nav_search import open_search_page, search_for_user, get_follow_status, click_follow
from helper import open_page 
from warmup import perform_scroll, perform_double_tap 
from database import log_action
from browse_reels import browse_reels_session
# Default logger
log = rprint

# --- CONSTANTS ---
ID_TAB_BAR = "com.instagram.android:id/tab_bar"
ID_GRID_IMAGE = "com.instagram.android:id/image_button"
# Post Count IDs
ID_POST_COUNT_FAMILIAR = "com.instagram.android:id/profile_header_familiar_post_count_value"
ID_POST_COUNT_STD = "com.instagram.android:id/row_profile_header_textview_post_count"

# --- HELPER: NAVIGATION RECOVERY ---
def return_to_base_state(driver):
    """
    Presses Back until the Bottom Tab Bar is visible.
    """
    log("[cyan]   * Nav: Returning to base state...[/cyan]")
    for i in range(5): 
        try:
            # U2 check exists
            if driver(resourceId=ID_TAB_BAR).exists(timeout=2):
                return True
            driver.press("back")
            time.sleep(1.5)
        except:
            driver.press("back")
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
    text = str(text).lower().strip().replace(',', '') # Ensure string
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
        
        # U2: Try finding either ID
        count_el = driver(resourceId=ID_POST_COUNT_FAMILIAR)
        if not count_el.exists:
            count_el = driver(resourceId=ID_POST_COUNT_STD)
        
        if count_el.exists:
            count_text = count_el.get_text()
            count = parse_count(count_text)
            log(f"[dim]Profile has {count} posts.[/dim]")
            
            if count < 1:
                log("[dim]Profile empty. Skipping content check.[/dim]")
                return
        
        # 2. Find Grid Images
        # U2 returns a list-like object for multiple matches
        images = driver(resourceId=ID_GRID_IMAGE)
        
        # Check if any exist (count is a property in U2 lists, sometimes len())
        # Safe way: exists() checks if at least one appears
        if not images.exists:
            log("[yellow]No images found (Private?).[/yellow]")
            return

        # 3. Determine how many to like
        # U2 .count gives number of matched elements
        total_images = images.count
        posts_to_like = min(total_images, 2)
        
        # 4. Fast Loop
        for i in range(posts_to_like):
            log(f"[blue]   * Vetting: checking post {i+1}...[/blue]")
            
            # Click the image (U2 allows index access)
            # Need to re-reference images inside loop just in case
            current_images = driver(resourceId=ID_GRID_IMAGE)
            if current_images.count <= i: break
            
            current_images[i].click()
            
            human_sleep(1.5, 2.5) 
            
            # 70% Chance to Like
            if chance(70):
                w, h = driver.window_size()
                # Double tap center
                perform_double_tap(driver, coords=(w//2, h//2))
                human_sleep(0.5, 1.0)

            # Back out
            driver.press("back")
            human_sleep(1.0, 1.5)

    except Exception as e:
        log(f"[red]Vetting Error: {e}[/red]")
        driver.press("back") # Emergency exit

def perform_follow_session(device, driver, targets_list, config, logger_func=None, state=None):
    """
    U2 Version of Follow Session.
    Note: 'device' arg removed/merged into logic if not needed, 
    but 'driver' is the U2 object now.
    """
    global log
    log = logger_func 

    if state is None:
        state = {"current_index": 0, "successful_follows": 0}
    # We need device_id for logging. 
    device_id = device.get('id')
    if not targets_list:
        log("[yellow]No targets provided for this session.[/yellow]")
        return

    log(f"[bold green]Starting Follow Session. Targets: {len(targets_list)}[/bold green]")
    successful_follows = 0
    
    for i in range(state["current_index"], len(targets_list)):
        username = targets_list[i] 
        try:
            log(f"\n[cyan]--- Processing {i+1}/{len(targets_list)}: {username} ---[/cyan]")

            # A. Pattern Break Logic
            if i > 0 and i % config['pattern_break'] == 0:
                log("[bold magenta]Taking a Pattern Break...[/bold magenta]")
                return_to_base_state(driver)
                if open_page(driver,'reels', logger_func=log):
                    browse_reels_session(driver, duration_minutes=1, logger_func=log)
                log("[magenta]Break over. Returning to Search.[/magenta]")

            # B. Navigate
            return_to_base_state(driver)
            
            # FIX: If search page fails, SKIP this user instead of stopping the whole session
            if not open_search_page(driver): 
                log(f"[red]Failed to open search page for {username}. Skipping.[/red]")
                continue
            
            # search_for_user needs to be updated to U2 in nav_search.py!
            if not search_for_user(driver, username):
                log(f"[red]Could not find user {username}. Marking failed.[/red]")
                log_action(device_id, username, "failed") 
                state["current_index"] = i + 1
                continue

            # C. Vetting
            log("[dim]Vetting profile layout...[/dim]")
            human_sleep(1, 2)
            perform_scroll(driver, direction="down", speed="normal") # Uses updated U2 scroll
            human_sleep(1, 2)
            
            # Get screen dimensions for swiping
            w, h = driver.window_size()
            
            if config.get('do_vetting', True):
                # Swipe UP to scroll DOWN to see grid
                # U2 swipe(startx, starty, endx, endy)
                driver.swipe(w//2, h*0.8, w//2, h*0.2, 0.5) 
                human_sleep(1, 2)
                vet_profile_content(driver)

            # Scroll back up to top to find follow button reliably
            driver.swipe(w//2, h*0.2, w//2, h*0.8, 0.5)
            human_sleep(1, 2)

            # D. Check Status & Follow
            # get_follow_status needs to be updated to U2 in nav_search.py!
            status = get_follow_status(driver)
            
            if status == "can_follow":
                log(f"[green]User is valid. Following...[/green]")
                if click_follow(driver):
                    log_action(device_id, username, "success")
                    successful_follows += 1
                    state["successful_follows"] += 1
                    delay = random.uniform(config['min_delay'], config['max_delay'])
                    log(f"[dim]Sleeping for {delay:.1f}s...[/dim]")
                    time.sleep(delay)
                else:
                    log("[red]Failed to click button.[/red]")
                
            elif status == "already_following":
                log("[yellow]Already following. Skipping.[/yellow]")
                log_action(device_id, username, "already_followed")
                
            else:
                log(f"[yellow]Status '{status}'. Skipping.[/yellow]")
                log_action(device_id, username, "ignored")

            state["current_index"] = i + 1
        except Exception as e:
            log(f"[bold red]CRITICAL ERROR processing user {username}: {e}[bold red]")
            log("[red]Attempting to recover and continue to next user...[/red]")
            try:
                driver.press("back")
                time.sleep(1)
                driver.press("back")
            except: pass
            continue

    log(f"[bold green]Session Complete. Followed: {successful_follows}[/bold green]")
