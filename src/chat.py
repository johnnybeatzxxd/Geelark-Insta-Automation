# chat.py

import time
import random
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from rich import print as rprint
from rich.console import Console
from helper import open_page
import logging
log = rprint
# Initialize rich console for better formatting
console = Console()

# --- Locators ---
# Chats List Screen
YOUR_MATCHES_TITLE_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_expiringConnectionsTitle")
YOUR_MATCHES_RV_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_connectionsListExpiring")
MATCH_ITEM_BUTTON_XPATH = ".//android.widget.Button[@resource-id='com.bumble.app:id/connectionItem_ringView']"
MAIN_CHAT_LIST_RV_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/connections_connectionsList")

# "Opening Move" Screen
OPENING_MOVE_CONTAINER_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/initialChatV3_container")
OPENING_MOVE_TITLE_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, 'Opening Move')]")
OPENING_MOVE_REPLY_BUTTON_LOCATOR = (AppiumBy.XPATH, "//android.view.View[@clickable='true' and .//android.widget.TextView[@text='Reply']]")


# Individual Chat Screen (Regular chat with input field) - UPDATED
CHAT_MESSAGE_INPUT_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatInput_text") # Updated from XML
# The Send button often appears dynamically. We'll use a content-desc for now.
# It might replace the voice message icon (com.bumble.app:id/recording_IconComponent)
CHAT_SEND_BUTTON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatInput_button_send") # NEW - More reliable
# Alternative if the above is too generic or if it has a specific ID when it appears:
# CHAT_SEND_BUTTON_LOCATOR_BY_ID_IF_AVAILABLE = (AppiumBy.ID, "com.bumble.app:id/id_of_the_send_button_when_visible")

CHAT_TOOLBAR_NAME_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/chatToolbar_title")
CHAT_HEADER_BACK_BUTTON_LOCATOR = (AppiumBy.XPATH, "//android.widget.ImageButton[@content-desc='Back']") # Toolbar back button

SPOTLIGHT_PROMO_TEXT_LOCATOR = (AppiumBy.XPATH, "//*[contains(@text, 'Spotlight is the easiest way')]")
OPENING_MOVES_SETUP_PROMO_TEXT_LOCATOR = (AppiumBy.XPATH, "//*[contains(@text, 'Get to good conversation, faster')]")

CHAT_24_HOURS_BANNER_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, 'hours to reply')]")

BEELINE_CARD_INNER_BUTTON_ID = "com.bumble.app:id/connectionItemBeeline_cards"
# --- Helper Functions ---
def is_beeline_card_currently_visible(driver, matches_rv_element):
    """
    Checks if the Beeline card (identified by its specific inner button ID)
    is currently visible within the provided "Your matches" RecyclerView element.

    Args:
        driver: The Appium WebDriver instance.
        matches_rv_element: The WebElement of the "Your matches" RecyclerView.

    Returns:
        bool: True if Beeline card's inner button is found and displayed, False otherwise.
    """
    try:
        # Look for the specific button ID that signifies a Beeline card
        # inside the passed RecyclerView element.
        beeline_inner_button = matches_rv_element.find_element(AppiumBy.ID, BEELINE_CARD_INNER_BUTTON_ID)
        if beeline_inner_button.is_displayed():
            log("[grey50]DEBUG (Beeline Visibility): Beeline card's inner button IS visible.[/grey50]")
            return True
        # log("[grey50]DEBUG (Beeline Visibility): Beeline card's inner button found but not displayed.[/grey50]")
        return False # Found but not displayed
    except NoSuchElementException:
        # log("[grey50]DEBUG (Beeline Visibility): Beeline card's inner button NOT found.[/grey50]")
        return False # Beeline card not present in the current view of the RV
    except Exception as e:
        log(f"[red]✗[/red] Error in is_beeline_card_currently_visible: {e}")
        return False # Err on the side of caution

def is_on_chats_list_page(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(YOUR_MATCHES_TITLE_LOCATOR)
        )
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(MAIN_CHAT_LIST_RV_LOCATOR)
        )
        log("[green]✓[/green] Verified on Chats list page")
        return True
    except TimeoutException:
        log("[red]✗[/red] Not on Chats list page (timed out waiting for elements)")
        return False

def handle_opening_move_screen(driver, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located(OPENING_MOVE_CONTAINER_LOCATOR),
                EC.presence_of_element_located(OPENING_MOVE_TITLE_TEXT_LOCATOR)
            )
        )
        log("[yellow]ℹ[/yellow] 'Opening Move' screen detected")
        reply_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(OPENING_MOVE_REPLY_BUTTON_LOCATOR)
        )
        reply_button.click()
        log("[green]✓[/green] Clicked 'Reply' on the 'Opening Move' screen")
        time.sleep(random.uniform(1.0, 2.0))
        return True
    except TimeoutException:
        return False
    except Exception as e:
        log(f"[red]✗[/red] Error handling 'Opening Move' screen: {e}")
        return False

def is_on_individual_chat_page(driver, user_name_for_verification=None, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(CHAT_MESSAGE_INPUT_LOCATOR)
        )
        log("[green]✓[/green] Verified on individual chat page (message input found)")

        if user_name_for_verification:
            try:
                toolbar_title_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located(CHAT_TOOLBAR_NAME_LOCATOR)
                )
                toolbar_title_text = toolbar_title_element.text
                expected_name_part = user_name_for_verification.split(',')[0].split(' ')[0]
                if expected_name_part.lower() in toolbar_title_text.lower():
                    log(f"[green]✓[/green] Verified chat toolbar title contains '{expected_name_part}'")
                else:
                    log(f"[yellow]⚠[/yellow] Chat toolbar title '{toolbar_title_text}' doesn't strongly match expected '{expected_name_part}'")
            except TimeoutException:
                log("[yellow]⚠[/yellow] Chat toolbar title element not found for secondary verification")
            except Exception as e_detail:
                log(f"[yellow]⚠[/yellow] Error during chat toolbar title verification: {e_detail}")
        return True
    except TimeoutException:
        log("[red]✗[/red] Not on individual chat page (timed out waiting for chat input)")
        return False

def send_opening_message(driver, match_name):
    """
    Types and sends an opening message by sending the whole string at once.
    Uses the specific resource-id for the send button.
    """
    log(f"[blue]→[/blue] Attempting to send opening message to {match_name}")
    try:
        # Wait for the message input field to be present and clickable
        message_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(CHAT_MESSAGE_INPUT_LOCATOR) 
            # CHAT_MESSAGE_INPUT_LOCATOR should be (AppiumBy.ID, "com.bumble.app:id/chatInput_text")
        )

        # Select a random message
        first_name = match_name.split(',')[0].split(' ')[0] # Get first name
        opening_lines = [
            "You look like you have a good voice, do you?",
            "If you were a drink what would you be? (I feel like tequila ngl)",
            "Idk what it is about you but bumble finally did smth right",
            "I'm already picturing our awkward first date, how exciting",
            "You have the vibe of someone who texts “wyd” at 2am",
            "You seem like the kind of guy who’d flirt with the bartender while I’m in the bathroom",
            "Not saying you’re my type but… my type is confused rn",
            "On a scale from gym rat to gamer, where do you fall",
            "You’re either super chill or a walking red flag, curious which",
            "I already regret texting you but here we are",
            "I matched just to see if you’d message first (you didn’t, shame)",
            "Guess I’ll start the convo since ur clearly shy",
            "Okay so how tall are you really",
            "Let’s settle this, pineapple on pizza: yes or no",
            "U look like you either surf or scam people idk",
            "I have a feeling you give the worst music recommendations, prove me wrong",
            "Not sure if you’re cute or if bumble’s algorithm just tricked me again",
            "Do you pass the vibe check or should I unmatch early",
            "You look like someone who doesn’t reply fast, am I right?",
            "I swiped for research purposes",
            "Don’t disappoint, I had high hopes (barely)",
            "Thought I’d break the ice before it melts",
            "I was gonna wait for you to text first but here we are",
            "If this convo flops, let’s blame the app",
            "Not sure why I swiped but now I’m curious",
            "Prove to me this app actually works sometimes",
        ]
        message_to_send = random.choice(opening_lines)

        # Click to focus
        message_input.click()
        time.sleep(0.5) # Allow UI to react

        # Clear placeholder text like "Aa" if present
        current_text_in_input = message_input.text
        if current_text_in_input and (current_text_in_input.lower() == "aa" or current_text_in_input.lower() == "send a message..."):
            log(f"[yellow]ℹ[/yellow] Clearing placeholder input text: '{current_text_in_input}'")
            message_input.clear()
            time.sleep(0.3) # Pause after clear

        # Send the entire message
        log(f"[blue]→[/blue] Typing message: '{message_to_send}'")
        message_input.send_keys(message_to_send)
        
        # Pause after typing, before attempting to send
        time.sleep(random.uniform(0.8, 1.5)) 

        # --- Attempt to click the SEND button using the specific ID ---
        try:
            # The send button should now be present and clickable with its specific ID
            send_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(CHAT_SEND_BUTTON_LOCATOR) # Using the new ID-based locator
            )
            send_button.click()
            log("[green]✓[/green] Message SENT.")
        except TimeoutException:
            log("[red]✗[/red] Send button (ID: com.bumble.app:id/chatInput_button_send) not found or not clickable after typing.")
            log("[grey50]DEBUG: Page source at send button failure:\n" + driver.page_source[:3000]) # Log some source
            return False

        time.sleep(random.uniform(1.0, 2.5)) # Pause after sending
        return True

    except TimeoutException:
        log(f"[red]✗[/red] Could not find message input field for {match_name}.")
        return False
    except Exception as e:
        log(f"[red]✗[/red] Unexpected error while sending message to {match_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def navigate_back_to_chats_list(driver, initial_back_presses=2, extra_back_press_if_needed=1):
    """
    Attempts to navigate back to the main chats list page.
    Performs initial back presses, then checks if still in a chat-like screen.
    If so, performs extra back presses before final verification.
    """
    total_presses_made = 0
    log(f"[blue]→[/blue] Navigating back to Chats list...")

    # Perform initial back presses
    for i in range(initial_back_presses):
        log(f"[blue]→[/blue] Performing back press #{total_presses_made + 1}...")
        driver.back()
        total_presses_made += 1
        # Shorter delay between these initial back presses
        time.sleep(random.uniform(0.5, 1.0))
        
        # Optional: Check if already on chats list after each press to exit early
        if is_on_chats_list_page(driver, timeout=1):
            log(f"[green]✓[/green] Returned to Chats list page after {total_presses_made} back press(es).")
            return True

    log(f"[blue]→[/blue] Performed {total_presses_made} initial back press(es). Checking current screen...")

    # Check if still on a chat-like screen (e.g., regular chat, "24 hours" banner visible)
    # We can use is_on_individual_chat_page or a more specific check for the banner
    still_on_chat_screen = False
    try:
        # Check for the "24 hours to reply" banner as a strong indicator
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(CHAT_24_HOURS_BANNER_TEXT_LOCATOR)
        )
        log("[yellow]⚠[/yellow] '24 hours to reply' banner still visible after initial back presses.")
        still_on_chat_screen = True
    except TimeoutException:
        # If banner not found, check if it's still on a generic individual chat page
        if is_on_individual_chat_page(driver, timeout=2): # Short timeout for this check
            log("[yellow]⚠[/yellow] Still on an individual chat page (input field found) after initial back presses.")
            still_on_chat_screen = True

    if still_on_chat_screen:
        log(f"[blue]→[/blue] Still on a chat-related screen. Performing {extra_back_press_if_needed} extra back press(es)...")
        for i in range(extra_back_press_if_needed):
            log(f"[blue]→[/blue] Performing extra back press #{i + 1} (total {total_presses_made + 1})...")
            driver.back()
            total_presses_made += 1
            time.sleep(random.uniform(0.8, 1.5)) # Longer pause after extra back presses
            
            if is_on_chats_list_page(driver, timeout=1):
                log(f"[green]✓[/green] Returned to Chats list page after {total_presses_made} total back press(es).")
                return True
    
    # Final verification: Are we on the chats list page?
    log(f"[blue]→[/blue] Total {total_presses_made} back press(es) performed. Final check for Chats list page...")
    if is_on_chats_list_page(driver, timeout=5):
        log("[green]✓[/green] Successfully returned to Chats list page.")
        return True
    else:
        # Last resort: try to use the open_page function if direct back presses failed
        log("[yellow]⚠[/yellow] Back presses did not land on Chats list. Attempting direct navigation via open_page('Chats')...")
        # Assuming open_page is imported from your helper module
        # from helper import open_page
        if 'open_page' in globals() and callable(globals()['open_page']): # Check if open_page is available
            if open_page(driver, "Chats"): # Ensure "Chats" is the correct content-desc for the tab
                log("[green]✓[/green] Successfully navigated to Chats page using open_page.")
                return True
            else:
                log("[red]✗[/red] Failed to return to Chats list page even with open_page.")
                return False
        else:
            log("[red]✗[/red] Failed to return to Chats list page. (open_page function not available for fallback).")
            return False

def get_screen_dimensions(driver):
    """Gets the current screen width and height."""
    try:
        window_size = driver.get_window_size()
        width = window_size.get('width')
        height = window_size.get('height')
        if width is None or height is None:
            log("[yellow]⚠[/yellow] Could not get window dimensions, using defaults.")
            return 1080, 1920 # Example defaults
        return int(width), int(height)
    except Exception as e:
        log(f"[red]✗[/red] Error getting screen dimensions: {e}")
        return 1080, 1920 # Fallback

def perform_horizontal_scroll_on_matches_list(driver, matches_rv_element, preferred_direction="left"):
    """
    Performs a horizontal scroll/swipe on the provided RecyclerView element
    with random distance and specified or random direction.

    Args:
        driver: The Appium WebDriver instance.
        matches_rv_element: The WebElement of the RecyclerView to scroll.
        preferred_direction (str): "left" (reveals items to the right), 
                                   "right" (reveals items to the left), or
                                   "random".
    Returns:
        bool: True if scroll was attempted, False on critical error.
    """
    screen_width, screen_height = get_screen_dimensions(driver)
    if not screen_width or not screen_height:
        log("[red]✗[/red] Cannot perform scroll, screen dimensions unknown.")
        return False

    try:
        location = matches_rv_element.location
        size = matches_rv_element.size

        # Element's y-center for the swipe
        element_y_center = location['y'] + size['height'] // 2
        element_y_center = max(0, min(element_y_center, screen_height -1)) # Ensure within screen

        # Determine actual scroll direction
        scroll_direction = preferred_direction
        if preferred_direction == "random":
            scroll_direction = random.choice(["left", "right"])

        # Randomize swipe distance (percentage of the element's width)
        # Make it significant to ensure a scroll occurs. E.g., 40% to 70% of element width.
        swipe_distance_percentage = random.uniform(0.40, 0.70)
        swipe_pixel_distance = int(size['width'] * swipe_distance_percentage)
        
        # Define swipe start and end points based on direction
        if scroll_direction == "left": # Swipe from Right-to-Left (reveals items on the Right)
            # Start near the right edge of the element, end near the left
            start_x = location['x'] + int(size['width'] * random.uniform(0.75, 0.85)) # e.g., 80%
            end_x = start_x - swipe_pixel_distance
            log(f"[grey50]Attempting to scroll content LEFT (revealing right items)[/grey50]")
        elif scroll_direction == "right": # Swipe from Left-to-Right (reveals items on the Left)
            # Start near the left edge of the element, end near the right
            start_x = location['x'] + int(size['width'] * random.uniform(0.15, 0.25)) # e.g., 20%
            end_x = start_x + swipe_pixel_distance
            log(f"[grey50]Attempting to scroll content RIGHT (revealing left items)[/grey50]")
        else:
            log(f"[yellow]⚠[/yellow] Unknown scroll direction '{scroll_direction}', defaulting to scroll left.")
            start_x = location['x'] + int(size['width'] * 0.8)
            end_x = start_x - swipe_pixel_distance # Default to scroll left


        # Ensure coordinates are within the element's horizontal bounds (and screen bounds)
        element_left_x = location['x']
        element_right_x = location['x'] + size['width']

        start_x = max(element_left_x + 5, min(start_x, element_right_x - 5)) # Add small buffer
        start_x = max(0, min(start_x, screen_width - 5)) # Screen bounds
        
        end_x = max(element_left_x + 5, min(end_x, element_right_x - 5))
        end_x = max(0, min(end_x, screen_width - 5))


        # If element is too narrow or swipe distance is too small, it might not scroll
        if abs(start_x - end_x) < int(screen_width * 0.1): # Less than 10% of screen width is too small
            log(f"[yellow]⚠[/yellow] Calculated swipe distance ({abs(start_x - end_x)}px) might be too small for a reliable scroll. Element width: {size['width']}.")
            # Could potentially abort or try a screen-based swipe as a fallback here if needed.
            # For now, we proceed with the calculated small swipe.

        duration_ms = random.randint(300, 600) # Randomize duration
        
        log(f"[grey50]Scrolling matches list: from ({start_x},{element_y_center}) to ({end_x},{element_y_center}), duration: ~{duration_ms}ms[/grey50]")
        
        # Using driver.swipe for simplicity, can be replaced with ActionChains if more control is needed
        driver.swipe(start_x, element_y_center, end_x, element_y_center, duration_ms)
        
        time.sleep(random.uniform(1.0, 2.0)) # Wait for scroll to complete and UI to settle
        return True
    except Exception as e:
        log(f"[red]✗[/red] Error during horizontal scroll on matches list: {e}")
        return False


# --- Main Processing Logic ---
def process_new_matches(driver, 
                        max_total_matches_to_process_this_run=None, 
                        max_consecutive_empty_scrolls=3,
                        logger_func: logging.Logger = rprint):
    """
    Scrolls the "Your matches" list. If Beeline card is visible, scrolls left.
    Otherwise, scrolls randomly. Picks one new, non-expired match and processes it.
    """
    global log
    log = logger_func

    if not is_on_chats_list_page(driver):
        log("[red]✗[/red] Not starting on Chats list page. Aborting match processing.")
        return

    log(f"[blue]→[/blue] Starting to process new matches by scrolling and random picking.")
    if max_total_matches_to_process_this_run is not None:
        log(f"[blue]→[/blue] Overall limit for this run: {max_total_matches_to_process_this_run} matches.")

    grand_total_processed_this_run = 0
    attempted_matches_content_descs_session = set()
    consecutive_empty_or_all_expired_scrolls = 0
    max_overall_iterations = 25 
    
    for iteration_num in range(max_overall_iterations):
        log(f"\n[cyan]--- Processing Iteration #{iteration_num + 1} ---[/cyan]")
        
        if max_total_matches_to_process_this_run is not None and \
           grand_total_processed_this_run >= max_total_matches_to_process_this_run:
            log(f"[yellow]ℹ[/yellow] Reached overall limit of {max_total_matches_to_process_this_run} matches processed.")
            break

        if not is_on_chats_list_page(driver, timeout=3):
            log("[red]✗[/red] No longer on Chats list page. Aborting.")
            break

        try:
            # --- CRITICAL: Fetch the RecyclerView element fresh in EACH iteration ---
            matches_rv_element = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located(YOUR_MATCHES_RV_LOCATOR)
            )

            # Check for promos that replace the entire list (like Spotlight)
            # This logic can be added here if needed, but we'll focus on Beeline for now.

            # Get the top-level clickable items in the carousel
            # Note: From your XML, both user matches (Button) and the Beeline card (FrameLayout) are direct children of the RecyclerView
            all_items_in_rv_view = matches_rv_element.find_elements(AppiumBy.XPATH, MATCH_ITEM_BUTTON_XPATH)
            
            # --- Filter for processable matches ---
            new_active_processable_matches = []
            for btn in all_items_in_rv_view:
                try:
                    if not btn.is_displayed(): continue
                    
                    # We only care about user match buttons for processing
                    if btn.get_attribute('resource-id') == "com.bumble.app:id/connectionItem_ringView":
                        desc = btn.get_attribute('content-desc')
                        is_expired_match = desc and "expired" in desc.lower()
                        if is_expired_match:
                            if desc: attempted_matches_content_descs_session.add(desc + "_EXPIRED_SKIPPED")
                            continue
                        
                        if desc and desc not in attempted_matches_content_descs_session:
                            new_active_processable_matches.append({'element': btn, 'desc': desc})
                except StaleElementReferenceException:
                    log("[yellow]⚠[/yellow] Stale element during filtering. Will retry iteration.")
                    new_active_processable_matches = "RETRY_ITERATION"
                    break

            if new_active_processable_matches == "RETRY_ITERATION":
                time.sleep(0.5); continue
            
            if not new_active_processable_matches:
                log("[yellow]ℹ[/yellow] No new, active, processable matches found in the current view.")
                consecutive_empty_or_all_expired_scrolls += 1
            else:
                log(f"[blue]→[/blue] Found {len(new_active_processable_matches)} new, active, processable match(es) in current view.")
                consecutive_empty_or_all_expired_scrolls = 0 # Reset counter since we found something

                # --- Pick one random match to process ---
                match_to_process_this_iteration = random.choice(new_active_processable_matches)
                current_match_element_to_click = match_to_process_this_iteration['element']
                current_match_desc = match_to_process_this_iteration['desc']
                attempted_matches_content_descs_session.add(current_match_desc)
                
                log(f"\n[magenta]--- Processing selected match: {current_match_desc} ---[/magenta]")
                try:
                    current_match_element_to_click.click()
                    # (The rest of your processing logic: go to chat, send message, navigate back)
                    time.sleep(random.uniform(1.5, 2.5)) 
                    if handle_opening_move_screen(driver): log("[green]✓[/green] Handled 'Opening Move' screen")
                    if is_on_individual_chat_page(driver, user_name_for_verification=current_match_desc):
                        if send_opening_message(driver, current_match_desc):
                            grand_total_processed_this_run += 1
                            log(f"[green]✓[/green] Successfully processed and messaged {current_match_desc}")
                        if not navigate_back_to_chats_list(driver): return # Critical error
                    else:
                        log(f"[red]✗[/red] Did not land on individual chat page for {current_match_desc}.")
                        if not navigate_back_to_chats_list(driver): return # Critical error
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception as click_err:
                    log(f"[red]✗[/red] Error processing match {current_match_desc}: {click_err}. Skipping.")
                    continue

            matches_rv_element = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located(YOUR_MATCHES_RV_LOCATOR)
            )
            # --- Scroll Logic for Next Iteration ---
            if consecutive_empty_or_all_expired_scrolls >= max_consecutive_empty_scrolls:
                log(f"[yellow]⚠[/yellow] Reached {max_consecutive_empty_scrolls} consecutive views with no new active matches. Stopping exploration.")
                break

            if iteration_num < max_overall_iterations - 1:
                # --- THIS IS THE KEY CHANGE ---
                # Check for Beeline card's presence *right before* deciding the scroll direction.
                # Use the fresh matches_rv_element we just fetched.
                scroll_direction_for_next = "random" 
                if is_beeline_card_currently_visible(driver, matches_rv_element):
                    scroll_direction_for_next = "left" 
                    log("[blue]→[/blue] Beeline card is visible, forcing scroll direction to LEFT.")
                else:
                    log("[blue]→[/blue] Beeline card not visible, next scroll direction will be RANDOM.")
                
                log(f"[blue]→[/blue] Performing horizontal scroll (preferred: {scroll_direction_for_next}) to find more...")
                if not perform_horizontal_scroll_on_matches_list(driver, matches_rv_element, preferred_direction=scroll_direction_for_next):
                    log("[red]✗[/red] Failed to scroll, cannot continue finding more matches.")
                    break
            else:
                log("[grey50]DEBUG: Max iterations reached, not scrolling further.[/grey50]")

        except TimeoutException:
            log("[yellow]⚠[/yellow] Timeout: 'Your matches' RecyclerView not found. May be empty or page changed.")
            break 
        except StaleElementReferenceException:
            log("[yellow]⚠[/yellow] StaleElementReferenceException in main loop. Retrying iteration.")
            time.sleep(1)
            continue
        except Exception as e:
            log(f"[red]✗[/red] Unexpected error in iteration #{iteration_num + 1}: {e}")
            import traceback; traceback.print_exc()
            break 
    
    log(f"\n[bold green]✓ Finished processing matches. Total successfully messaged: {grand_total_processed_this_run}[/bold green]")
if __name__ == "__main__":
    caps = {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:deviceName": "emulator-5554",
        "appium:appPackage": "com.bumble.app",
        "appium:noReset": True,
        "appium:newCommandTimeout": 300
    }
    appium_server_url = 'http://127.0.0.1:4723'
    driver = None
    try:
        options = UiAutomator2Options().load_capabilities(caps)
        log("[blue]→[/blue] Connecting to Appium driver...")
        driver = webdriver.Remote(appium_server_url, options=options)
        log("[green]✓[/green] Driver connected")
        
        log("[yellow]ℹ[/yellow] Please navigate to the 'Chats' tab in Bumble")
        log("[yellow]ℹ[/yellow] Waiting for 10 seconds...")
        time.sleep(10)

        if is_on_chats_list_page(driver):
            log("[green]✓[/green] Starting match processing")
            process_new_matches(driver, max_matches_to_process=2)
        else:
            log("[red]✗[/red] Not on Chats list page. Please check app state")

        log("\n[yellow]ℹ[/yellow] Test finished. Check console for detailed logs")
        log("[yellow]ℹ[/yellow] Keeping app open for observation...")
        time.sleep(15)
    except Exception as e:
        log(f"[red]✗[/red] Critical error in main test block: {e}")
        import traceback
        traceback.print_exc()
        if driver:
            try:
                ts = time.strftime("%Y%m%d-%H%M%S")
                driver.save_screenshot(f"chat_error_{ts}.png")
                with open(f"chat_error_source_{ts}.xml", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                log(f"[green]✓[/green] Saved error debug info ({ts})")
            except Exception as e_save:
                log(f"[red]✗[/red] Could not save error debug info: {e_save}")
    finally:
        if driver:
            log("[blue]→[/blue] Quitting driver")
            driver.quit()
