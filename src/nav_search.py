import time
from rich import print as rprint
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# --- IDS ---
ID_SEARCH_TAB = "com.instagram.android:id/search_tab"
ID_SEARCH_INPUT = "com.instagram.android:id/action_bar_search_edit_text"
ID_SEARCH_RESULT_USERNAME = "com.instagram.android:id/row_search_user_username"
ID_PROFILE_TITLE = "com.instagram.android:id/action_bar_title"
ID_FOLLOW_BUTTON = "com.instagram.android:id/profile_header_follow_button"
ID_TAB_BAR = "com.instagram.android:id/tab_bar" # Needed to know if we are back at base

log = rprint

def open_search_page(driver):
    """Navigates to the search tab."""
    try:
        # If we are already on search page (input box visible), just return true
        if driver.find_elements(AppiumBy.ID, ID_SEARCH_INPUT):
            return True

        tab = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((AppiumBy.ID, ID_SEARCH_TAB))
        )
        tab.click()
        time.sleep(2)
        return True
    except:
        log("[red]Failed to find Search Tab.[/red]")
        return False


def search_for_user(driver, username):
    """
    Types '@username' for precision, compares 'username' for matching.
    """
    # Clean the input username (remove @ just in case it was in the file)
    clean_username = username.strip().replace("@", "").lower()
    # Create the search string (with @)
    search_query = f"@{clean_username}"

    try:
        # 1. Activate Search Box (Retry Logic)
        search_box = None
        for attempt in range(3):
            try:
                search_box = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((AppiumBy.ID, ID_SEARCH_INPUT))
                )
                search_box.click()
                time.sleep(1)
                search_box.clear()
                
                # --- CHANGE 1: Send the query with @ ---
                search_box.send_keys(search_query) 
                
                try: driver.execute_script('mobile: performEditorAction', {'action': 'search'})
                except: pass
                
                break
            except StaleElementReferenceException:
                time.sleep(1)
            except Exception as e:
                log(f"[red]Error interaction with search box: {e}[/red]")
                return False
        
        log(f"[dim]Searching for '{search_query}'...[/dim]")
        time.sleep(3.5) 

        # 2. INTELLIGENT MATCHING
        found_match = False
        results = driver.find_elements(AppiumBy.ID, ID_SEARCH_RESULT_USERNAME)
        
        if not results:
            log("[yellow]No results found in list.[/yellow]")
            return False

        for res in results:
            try:
                # Get text from UI (which usually won't have @)
                res_text = res.text.strip().lower()
                # log(f"[blue]Result: {res_text}[/blue]") # Debug log
                
                # --- CHANGE 2: Compare clean text vs clean target ---
                if res_text == clean_username:
                    log(f"[green]Found match: {res.text}[/green]")
                    res.click()
                    found_match = True
                    break
            except: continue 

        if not found_match:
            log(f"[yellow]Target '{clean_username}' not found in top results.[/yellow]")
            return False

        # 3. Verify Landing
        try:
            # Wait for title. Note: Title usually doesn't have @ either.
            WebDriverWait(driver, 5).until(
                EC.text_to_be_present_in_element(
                    (AppiumBy.ID, ID_PROFILE_TITLE), clean_username
                )
            )
            return True
        except:
            log(f"[red]Clicked result but profile title mismatch.[/red]")
            return False

    except Exception as e:
        log(f"[red]Search Routine Error: {e}[/red]")
        return False

def get_follow_status(driver):
    """
    Checks the button on the profile.
    """
    try:
        btn = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((AppiumBy.ID, ID_FOLLOW_BUTTON))
        )
        text = btn.text.lower()
        
        if text == "follow" or text == "follow back":
            return "can_follow"
        elif "following" in text:
            return "already_following"
        elif "requested" in text:
            return "requested"
        
        return "unknown"
    except:
        return "not_found"

def click_follow(driver):
    try:
        btn = driver.find_element(AppiumBy.ID, ID_FOLLOW_BUTTON)
        btn.click()
        return True
    except: 
        try:
            btn = WebDriverWait(driver,5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(@text, 'Follow')]")))
            btn.click()
            return True
        except:
            return False
    return False
