import time
import uiautomator2 as u2
from rich import print as rprint

log = rprint

# --- CONSTANTS ---
APP_PACKAGE = "com.instagram.android"
NAV_BAR_ID = "com.instagram.android:id/tab_bar"

# Mapping: Page Name -> Resource ID
TAB_ID_MAP = {
    "HOME": "com.instagram.android:id/feed_tab",
    "REELS": "com.instagram.android:id/clips_tab",
    "MESSAGE": "com.instagram.android:id/direct_tab",
    "SEARCH": "com.instagram.android:id/search_tab",
    "PROFILE": "com.instagram.android:id/profile_tab"
}

# --- HELPER: POPUP HANDLING ---
def handle_common_popups(driver):
    """
    Checks for and closes common Instagram interruptions.
    """
    dismiss_texts = ["Not now", "Cancel", "Deny", "Don't Allow", "No, thanks", "Later", "Dismiss"]
    clicked = False
    
    for text_val in dismiss_texts:
        # Check if exists (fast check)
        if driver(text=text_val).exists(timeout=0.5):
            log(f"[yellow]Detected popup: '{text_val}'. Clicking...[/yellow]")
            driver(text=text_val).click()
            clicked = True
            time.sleep(1)
            
    return clicked

# ==============================================================================
# UPDATED NAVIGATION LOGIC (U2 VERSION)
# ==============================================================================

def is_nav_bar_present(driver, timeout=3):
    return driver(resourceId=NAV_BAR_ID).exists(timeout=timeout)

def get_current_screen_by_tab(driver, timeout=5):
    """
    Determines current screen by checking which tab has 'selected=true'.
    """
    try:
        # 1. Find the selected tab
        # We search for ANY element that is selected=True inside the nav bar
        selected = driver(selected=True)
        
        if selected.exists(timeout=timeout):
            # Iterate through our known tabs to see which one is selected
            for name, tab_id in TAB_ID_MAP.items():
                # Check if the element with this ID is selected
                if driver(resourceId=tab_id, selected=True).exists(timeout=0.1):
                    return f"{name}_SCREEN"
                
                # Check if a CHILD of this ID is selected (Profile icon case)
                xpath = f"//*[@resource-id='{tab_id}']//*[@selected='true']"
                if driver.xpath(xpath).exists:
                    return f"{name}_SCREEN"

    except Exception:
        pass

    # --- METHOD 2: FALLBACK CONTEXT ---
    try:
        # Profile specific: "Edit profile" button
        if driver(resourceId="com.instagram.android:id/edit_name_and_bio_description").exists(timeout=1):
            return "PROFILE_SCREEN"
        
        # Search specific: Search input
        if driver(resourceId="com.instagram.android:id/action_bar_search_edit_text").exists(timeout=1):
            return "SEARCH_SCREEN"
            
    except: pass

    return "UNKNOWN_SCREEN"

def open_page(driver, page_name_from_ui, navigation_timeout=10, verification_timeout=5, logger_func=rprint):
    """
    Navigates to the specified page using U2 commands.
    """
    global log
    log = logger_func
    
    target_key = page_name_from_ui.upper().strip()
    target_screen_id = f"{target_key}_SCREEN"
    
    if target_key not in TAB_ID_MAP:
        log(f"[red]Error: '{page_name_from_ui}' is not valid.[/red]")
        return False

    target_resource_id = TAB_ID_MAP[target_key]
    max_retries = 1 

    for attempt in range(max_retries + 1):
        try:
            log(f"[yellow]Attempt {attempt+1}: Opening '{target_key}'...[/yellow]")

            # 1. Ensure App is Running (Fast in U2)
            current_app = driver.app_current()
            if current_app['package'] != APP_PACKAGE:
                driver.app_start(APP_PACKAGE)
                driver.app_wait(APP_PACKAGE, timeout=10)

            # 2. Check if already there
            if get_current_screen_by_tab(driver, timeout=2) == target_screen_id:
                log(f"[green]Already on '{target_key}' page.[/green]")
                return True
            
            # 3. Handle Popups
            if not is_nav_bar_present(driver, timeout=2):
                log("[yellow]Nav bar blocked. Checking popups...[/yellow]")
                handle_common_popups(driver)

            # 4. Click the Tab
            log(f"[yellow]Clicking '{target_key}' tab...[/yellow]")
            
            # U2 Click with wait
            if not driver(resourceId=target_resource_id).exists(timeout=navigation_timeout):
                # If tab not found, try clearing popups again
                handle_common_popups(driver)
                
            driver(resourceId=target_resource_id).click(timeout=navigation_timeout)

            # 5. VERIFICATION STAGE
            verified = False
            start_verify = time.time()
            while time.time() - start_verify < verification_timeout:
                if get_current_screen_by_tab(driver, timeout=0.5) == target_screen_id:
                    verified = True
                    break
                time.sleep(0.5)
            
            if verified:
                log(f"[green]Successfully navigated to '{target_key}'.[/green]")
                return True
            
            # Intervention Logic
            log(f"[red]Verification failed. Checking popups...[/red]")
            if handle_common_popups(driver):
                time.sleep(1)
                # Check again
                if get_current_screen_by_tab(driver, timeout=2) == target_screen_id:
                    log(f"[green]Recovered![/green]")
                    return True
            
            raise Exception("Navigation Verification Failed")

        except Exception as e:
            log(f"[red]Attempt {attempt+1} failed: {e}[/red]")
            
            if attempt < max_retries:
                log(f"[bold red]!!! RESTARTING INSTAGRAM !!![/bold red]")
                driver.app_stop(APP_PACKAGE)
                time.sleep(1)
                driver.app_start(APP_PACKAGE)
            else:
                log(f"[bold red]All attempts to open '{target_key}' failed.[/bold red]")
                return False
                
    return False
