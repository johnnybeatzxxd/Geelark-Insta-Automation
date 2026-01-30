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

def open_page(driver, page_name_from_ui, navigation_timeout=5, verification_timeout=3, logger_func=rprint):
    """
    Optimized U2 Navigation: Minimal hierarchy dumps for maximum speed.
    """
    global log
    log = logger_func
    
    target_key = page_name_from_ui.upper().strip()
    target_screen_id = f"{target_key}_SCREEN"
    
    if target_key not in TAB_ID_MAP:
        return False

    target_id = TAB_ID_MAP[target_key]

    try:
        # 1. OPTIMISTIC CLICK (The Speed Secret)
        # We don't check if we are already there. We just click. 
        # Clicking the tab we are already on does nothing in IG, so it's safe.
        log(f"[yellow]Navigating to {target_key}...[/yellow]")
        
        # We use a very short timeout. If the tab bar is visible, this is instant.
        tab = driver(resourceId=target_id)
        if tab.exists(timeout=1):
            tab.click()
        else:
            # ONLY if the tab isn't found do we handle popups (Saves 2-3 seconds)
            log("[dim]Tab bar not found, clearing popups...[/dim]")
            handle_common_popups(driver)
            tab.click(timeout=3)

        # 2. FAST VERIFICATION
        # Instead of a complex loop, we check for a "Success Signal"
        # For Search, it's the search box. For Home, it's the logo, etc.
        
        # We check the specific 'selected' state for the target tab only
        if driver(resourceId=target_id, selected=True).wait(timeout=verification_timeout):
            log(f"[green]Successfully on {target_key}.[/green]")
            return True
            
        # 3. FALLBACK VERIFICATION (If 'selected' state is laggy)
        if get_current_screen_by_tab(driver, timeout=1) == target_screen_id:
            return True

        # 4. LAST RESORT: RECOVERY
        log(f"[red]Failed to verify {target_key}. Restarting app...[/red]")
        driver.app_stop(APP_PACKAGE)
        driver.app_start(APP_PACKAGE)
        # Recursive call for one retry
        return driver(resourceId=target_id).click(timeout=5)

    except Exception as e:
        log(f"[red]Nav Error: {e}[/red]")
        return False
