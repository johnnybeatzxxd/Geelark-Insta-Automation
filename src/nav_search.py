import time
from rich import print as rprint

# --- IDS ---
ID_SEARCH_TAB = "com.instagram.android:id/search_tab"
ID_SEARCH_INPUT = "com.instagram.android:id/action_bar_search_edit_text"
ID_SEARCH_RESULT_USERNAME = "com.instagram.android:id/row_search_user_username"
ID_PROFILE_TITLE = "com.instagram.android:id/action_bar_title"
ID_FOLLOW_BUTTON = "com.instagram.android:id/profile_header_follow_button"
ID_TAB_BAR = "com.instagram.android:id/tab_bar"  # Needed to know if we are back at base

log = rprint


def open_search_page(driver):
    """Navigates to the search tab. (U2 Version)"""
    try:
        # If we are already on search page (input box visible), just return true
        if driver(resourceId=ID_SEARCH_INPUT).exists(timeout=2):
            return True

        # Wait for and click the search tab
        tab = driver(resourceId=ID_SEARCH_TAB)
        if tab.wait(timeout=5):
            tab.click()
            time.sleep(2)
            return True
        else:
            log("[red]Failed to find Search Tab.[/red]")
            return False
    except Exception as e:
        log(f"[red]Failed to open search page: {e}[/red]")
        return False


def search_for_user(driver, username):
    """
    Types '@username' for precision, compares 'username' for matching.
    (U2 Version)
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
                search_box = driver(resourceId=ID_SEARCH_INPUT)
                if search_box.wait(timeout=5):
                    search_box.click()
                    time.sleep(1)
                    search_box.clear_text()
                    
                    # Send the query with @
                    search_box.set_text(search_query)
                    
                    # Execute Search Action (equivalent to mobile: performEditorAction {'action': 'search'})
                    driver.press("search")
                    
                    break
                else:
                    time.sleep(1)
            except Exception as e:
                if attempt == 2:
                    log(f"[red]Error interacting with search box: {e}[/red]")
                    return False
                time.sleep(1)
        
        log(f"[dim]Searching for '{search_query}'...[/dim]")
        time.sleep(3.5) 

        # 2. INTELLIGENT MATCHING
        found_match = False
        results = driver(resourceId=ID_SEARCH_RESULT_USERNAME)
        
        if not results.exists:
            log("[yellow]No results found in list.[/yellow]")
            return False

        # Iterate through results
        for i in range(results.count):
            try:
                res = results[i]
                # Get text from UI (which usually won't have @)
                res_text = res.get_text()
                if res_text:
                    res_text = res_text.strip().lower()
                    
                    # Compare clean text vs clean target
                    if res_text == clean_username:
                        log(f"[green]Found match: {res_text}[/green]")
                        res.click()
                        found_match = True
                        break
            except Exception:
                continue 

        if not found_match:
            log(f"[yellow]Target '{clean_username}' not found in top results.[/yellow]")
            return False

        # 3. Verify Landing
        time.sleep(2)  # Wait for profile to load
        try:
            title_el = driver(resourceId=ID_PROFILE_TITLE)
            if title_el.wait(timeout=5):
                title_text = title_el.get_text()
                if title_text and clean_username in title_text.lower():
                    return True
                else:
                    log(f"[red]Clicked result but profile title mismatch.[/red]")
                    return False
            else:
                log(f"[red]Profile title not found.[/red]")
                return False
        except Exception:
            log(f"[red]Clicked result but profile title mismatch.[/red]")
            return False

    except Exception as e:
        # Just log the error and return False to let the main loop handle it (skip user)
        # We do NOT raise here anymore, to prevent crashing the worker loop.
        log(f"[red]Search Routine Error: {e}[/red]")
        return False


def get_follow_status(driver):
    """
    Checks the button on the profile. (U2 Version)
    """
    try:
        btn = driver(resourceId=ID_FOLLOW_BUTTON)
        if btn.wait(timeout=3):
            text = btn.get_text()
            if text:
                text = text.lower()
                
                if text == "follow" or text == "follow back":
                    return "can_follow"
                elif "following" in text:
                    return "already_following"
                elif "requested" in text:
                    return "requested"
            
            return "unknown"
        else:
            return "not_found"
    except Exception:
        return "not_found"


def click_follow(driver):
    """Clicks the follow button and handles popups. (U2 Version)"""
    log("[dim]Initiating Follow sequence...[/dim]")
    
    try:
        # --- STEP 1: Click the Main Profile Button ---
        try:
            main_btn = driver(resourceId=ID_FOLLOW_BUTTON)
            if main_btn.wait(timeout=3):
                main_btn.click()
                log("[blue]Clicked main profile button.[/blue]")
            else:
                log("[red]Could not find main follow button.[/red]")
                return False
        except Exception as e:
             # Just log and fail safely
            log(f"[red]Could not find main follow button: {e}[/red]")
            return False

        # --- STEP 2: Handle Potential "Review Info" Popup ---
        time.sleep(2)  # Wait for animation/popup to trigger

        # Check if the main button successfully changed
        main_btn = driver(resourceId=ID_FOLLOW_BUTTON)
        # We assume if it exists we check text, if not maybe popup covers it? 
        # But U2 finding usually works even with popup if it's in hierarchy.
        if main_btn.exists:
            status_text = main_btn.get_text()
            if status_text:
                status_text = status_text.lower()

                if "following" in status_text or "requested" in status_text:
                    log("[green]Success: Status changed to Following/Requested immediately.[/green]")
                    return True
        
        # If we are here, the status didn't change, so a Popup is likely open.
        log("[yellow]Status didn't change. Looking for Popup button...[/yellow]")

        # --- STEP 3: Find the Popup Button ---
        # U2 uses UiSelector syntax directly
        popup_btn = driver(text="Follow", clickable=True)
        if popup_btn.wait(timeout=3):
            popup_btn.click()
            log("[green]Clicked 'Follow' inside the popup.[/green]")
            return True
        else:
            log("[yellow]No popup button found, assuming follow worked.[/yellow]")
            return True

    except Exception as e:
        # Just log the error and return False to let the main loop handle it (skip user)
        log(f"[red]Follow sequence failed: {e}[/red]")
        return False
