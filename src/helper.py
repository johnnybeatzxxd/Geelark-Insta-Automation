from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich import print as rprint
import time 
import random
import logging

log = rprint

# --- CONSTANTS ---
APP_PACKAGE = "com.instagram.android"
NAV_BAR_ID = "com.instagram.android:id/tab_bar" 

# ID Mapping (These remain the same, they are the containers)
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
    # Simplified list
    dismiss_texts = ["Not now", "Cancel", "Deny", "Don't Allow", "No, thanks", "Later", "Dismiss"]
    
    # Constructing XPath safely
    # This checks for Buttons OR TextViews that contain the text
    xpath_conditions = " or ".join([f"contains(@text, '{t}')" for t in dismiss_texts])
    xpath_query = f"//android.widget.Button[{xpath_conditions}] | //android.widget.TextView[@clickable='true' and ({xpath_conditions})]"

    try:
        popup_btn = WebDriverWait(driver, 1.5).until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath_query))
        )
        log(f"[yellow]Detected popup: '{popup_btn.text}'. Clicking...[/yellow]")
        popup_btn.click()
        time.sleep(1)
        return True
    except:
        return False

# ==============================================================================
# [REMOVE LATER] OLD BUMBLE FUNCTIONS
# ==============================================================================
def get_screen_dimensions(driver):
    try:
        window_size = driver.get_window_size()
        return int(window_size.get('width')), int(window_size.get('height'))
    except: return None, None
def handle_adjust_filters_prompt(driver, timeout=3): return False
def adjust_age_filter_and_apply(driver, timeout=15): return False 

# ==============================================================================
# UPDATED NAVIGATION LOGIC
# ==============================================================================

def is_nav_bar_present(driver, timeout=3):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.ID, NAV_BAR_ID))
        )
        return True
    except:
        return False

def get_current_screen_by_tab(driver: webdriver.Remote, timeout=5):
    """
    Determines current screen. 
    1. Robust 'Selected Tab' detection (handles Profile nesting).
    2. Fallback 'Page Element' detection (if Tab bar logic fails).
    """
    
    # --- METHOD 1: CHECK THE TABS (Preferred) ---
    try:
        # Strategy: Find ANY element inside the tab bar that is selected='true'.
        # Then, check if that element OR its ancestors match our known TAB IDs.
        # This solves the Profile issue where the selected image is 3 layers deep.
        
        xpath_selected_item = f"//*[@resource-id='{NAV_BAR_ID}']//*[@selected='true']"
        
        selected_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((AppiumBy.XPATH, xpath_selected_item))
        )
        
        # We found the highlighted icon/box. Now we need to know which TAB it belongs to.
        # We check the element's ID, and if that doesn't match, we check its parent, and grandparent.
        
        # Get the ID of the selected element
        found_id = selected_element.get_attribute("resource-id")
        
        # Check against our map immediately
        for name, tab_id in TAB_ID_MAP.items():
            if found_id == tab_id:
                return f"{name}_SCREEN"

        # If the selected element is the ICON (e.g. tab_avatar), we need to search up the tree
        # to find the container ID (e.g. profile_tab)
        # Using XPath to check ancestors against our known IDs
        for name, tab_id in TAB_ID_MAP.items():
            # Does this selected element have an ancestor with this ID?
            has_ancestor = selected_element.find_elements(AppiumBy.XPATH, f"./ancestor::*[@resource-id='{tab_id}']")
            if has_ancestor:
                return f"{name}_SCREEN"
                
    except TimeoutException:
        # No tab appears selected. This happens on some screens or if a popup is covering it.
        pass
    except Exception as e:
        log(f"[yellow]Debug: Tab detection error: {e}[/yellow]")

    # --- METHOD 2: FALLBACK - CONTEXTUAL ELEMENTS (If Tab logic fails) ---
    # If the user is on the Profile page, the "Edit profile" button usually exists.
    try:
        # Check for Profile Page specific elements
        profile_indicator = driver.find_elements(AppiumBy.ID, "com.instagram.android:id/edit_name_and_bio_description")
        if profile_indicator:
            return "PROFILE_SCREEN"
            
        # Check for Search Page specific elements (Search box)
        search_indicator = driver.find_elements(AppiumBy.ID, "com.instagram.android:id/action_bar_search_edit_text")
        if search_indicator:
            return "SEARCH_SCREEN"

    except:
        pass

    return "UNKNOWN_SCREEN"

def open_page(driver: webdriver.Remote, page_name_from_ui, navigation_timeout=10, verification_timeout=5, logger_func: logging.Logger = rprint):
    """
    Navigates to the specified page with Popup Intervention and Retry Logic.
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

            # 1. Ensure App is Running
            driver.activate_app(APP_PACKAGE)
            if attempt > 1: time.sleep(2) 

            # 2. Check if already there (Fast Check)
            if get_current_screen_by_tab(driver, timeout=2) == target_screen_id:
                log(f"[green]Already on '{target_key}' page.[/green]")
                return True
            
            # 3. Handle Popups BEFORE clicking (In case a popup is blocking the tab bar)
            if not is_nav_bar_present(driver, timeout=2):
                log("[yellow]Nav bar blocked or missing. Checking popups...[/yellow]")
                handle_common_popups(driver)

            # 4. Click the Tab
            log(f"[yellow]Clicking '{target_key}' tab...[/yellow]")
            tab_element = WebDriverWait(driver, navigation_timeout).until(
                EC.element_to_be_clickable((AppiumBy.ID, target_resource_id))
            )
            tab_element.click()

            # 5. VERIFICATION STAGE (With Popup Intervention)
            try:
                WebDriverWait(driver, verification_timeout).until(
                    lambda d: get_current_screen_by_tab(d, timeout=1) == target_screen_id
                )
                log(f"[green]Successfully navigated to '{target_key}'.[/green]")
                return True
            
            except TimeoutException:
                # --- CRITICAL FIX: INTERVENTION ---
                log(f"[red]Verification failed for '{target_key}'. Checking for blocking popups...[/red]")
                
                # Try to handle a popup that might have appeared AFTER clicking (like "Sync Contacts")
                if handle_common_popups(driver):
                    log(f"[green]Popup handled! verifying navigation again...[/green]")
                    time.sleep(1) # Wait for popup to go away
                    
                    # Try verification one last time
                    try:
                        if get_current_screen_by_tab(driver, timeout=3) == target_screen_id:
                            log(f"[green]Recovered! Now on '{target_key}'.[/green]")
                            return True
                    except:
                        pass # Verification failed again, proceed to raise error
                
                # If we are here, either no popup was found, or verification failed twice
                raise TimeoutException("Navigation failed even after checking for popups.")

        except (TimeoutException, NoSuchElementException, Exception) as e:
            log(f"[red]Attempt {attempt+1} failed: {e}[/red]")
            
            # Only restart if we have retries left
            if attempt < max_retries:
                log(f"[bold red]!!! RESTARTING INSTAGRAM !!![/bold red]")
                try:
                    driver.terminate_app(APP_PACKAGE)
                    time.sleep(2)
                except: pass
            else:
                log(f"[bold red]All attempts to open '{target_key}' failed.[/bold red]")
                return False

    return False
