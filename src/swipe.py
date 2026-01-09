import random
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException # Added TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from helper import handle_adjust_filters_prompt
from helper import adjust_age_filter_and_apply
from helper import get_screen_dimensions
from rich import print as rprint
import logging

log = rprint

# Using a distinctive text on the ad screen for initial detection
PREMIUM_AD_IDENTIFIER_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[@text=\"Find who you're looking for, faster\"]")

# The "Maybe later" button is a clickable View containing a TextView with text "Maybe later"
PREMIUM_AD_MAYBE_LATER_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.view.View[@clickable='true' and .//android.widget.TextView[@text=\"Maybe later\"]]"
)
# --- Locators for the SuperSwipe Info Popup ---
# Using a distinctive text on the popup for initial detection
SUPERSWIPE_POPUP_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[@text=\"Supercharge your chance to match\"]"
)

# The "Got it" button is a clickable View containing a TextView with text "Got it"
SUPERSWIPE_POPUP_GOT_IT_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.view.View[@clickable='true' and .//android.widget.TextView[@text=\"Got it\"]]"
)

# Alternative: Close button at the top right of the popup content area
SUPERSWIPE_POPUP_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.XPATH,
    "//android.widget.ImageView[@content-desc='Close' and @clickable='true']"
)

FIRST_MOVE_SCREEN_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[contains(@text, \"It's time to\") and contains(@text, \"make your move\")]"
) 
FIRST_MOVE_SCREEN_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.ID, "com.bumble.app:id/navbar_button_navigation"
)

ITS_A_MATCH_SCREEN_IDENTIFIER_TEXT = (AppiumBy.XPATH, "//*[@resource-id='com.bumble.app:id/match_explanationTitle' and @text='What a match!']")
# Or by container ID if more stable:
# ITS_A_MATCH_SCREEN_CONTAINER_ID = (AppiumBy.ID, "com.bumble.app:id/mutualAttraction_topContainer")

# "Opening Moves" info box elements (if present on the "It's a Match!" screen)
OPENING_MOVES_INFO_BOX_TEXT_LOCATOR = (AppiumBy.XPATH, "//android.widget.TextView[@text='Kick things off with Opening Moves']")
OPENING_MOVES_INFO_BOX_GOT_IT_BUTTON_LOCATOR = (
    AppiumBy.XPATH,
    "//androidx.compose.ui.platform.ComposeView[.//android.widget.TextView[@text='Kick things off with Opening Moves']]//android.view.View[@clickable='true' and .//android.widget.TextView[@text='Got it']]"
) # This XPath is more specific to the "Got it" within the "Opening Moves" box

# Main "Close" button for the entire "It's a Match!" screen (top left)
ITS_A_MATCH_MAIN_CLOSE_BUTTON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/match_close")

MATCH_SCREEN_MINI_COMPOSER_INPUT_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/composerMini_text")
MATCH_SCREEN_MINI_COMPOSER_SEND_ICON_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/composerMini_icon")

BEST_PHOTO_POPUP_IDENTIFIER_TEXT_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.TextView[@text='Put your best photo first']"
)
# The "Save and close" button
BEST_PHOTO_POPUP_SAVE_AND_CLOSE_BUTTON_LOCATOR = (
    AppiumBy.XPATH, 
    "//android.widget.Button[@text='Save and close']"
)

PROFILE_CARD_LOADED_INDICATOR_XPATH = (
    "//*[@resource-id='com.bumble.app:id/encountersGridItem_summaryContainer' or "
    "@resource-id='com.bumble.app:id/encountersGridItem_aboutContainer']"
)

NAV_BAR_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/mainApp_navigationTabBar")
# Bumble logo, typical of the swipe screen
NAVBAR_LOGO_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/navbar_logo")

PROFILE_SCROLL_CONTAINER_LOCATOR = (

    AppiumBy.ID,
    "com.bumble.app:id/encountersGridProfile_list"
)
SELECTED_PEOPLE_TAB_LOCATOR = (
    AppiumBy.XPATH,
    "//android.view.ViewGroup[@content-desc='People' and @selected='true']"
)

OUT_OF_LIKES_HEADER_LOCATOR = (
    AppiumBy.XPATH,
    "//android.widget.TextView[@text='You’re all out of likes']"
)

LOADING_SKELETON_LOCATOR = (
    AppiumBy.XPATH, 
    "//androidx.compose.ui.platform.ComposeView/android.view.View/android.view.View"
)

PROFILE_SUMMARY_CONTAINER_LOCATOR = (AppiumBy.ID, "com.bumble.app:id/encountersGridItem_summaryContainer")

def is_profile_loading(driver, timeout_sec=0.5):
    """
    Checks if the app is in the state of loading a new profile.

    This is defined as being on the "People" tab BUT the final profile summary
    container has NOT yet appeared.

    Args:
        driver: The Appium WebDriver instance.
        timeout_sec (float): A very short time to wait for the check.

    Returns:
        bool: True if the app is currently loading a profile, False otherwise.
    """
    try:
        # 1. First, quickly confirm we are on the correct "People" screen.
        # If we aren't, then we definitely aren't loading a profile.
        WebDriverWait(driver, 0.2).until(
            EC.presence_of_element_located(SELECTED_PEOPLE_TAB_LOCATOR)
        )

        # 2. Now, attempt to find the loaded profile's main content container.
        WebDriverWait(driver, timeout_sec).until(
            EC.presence_of_element_located(PROFILE_SUMMARY_CONTAINER_LOCATOR)
        )
        
        # If the line above SUCCEEDED, it means the profile is already loaded.
        # Therefore, we are NOT in a loading state.
        log("[grey50]Profile is already loaded, not in a loading state.[/grey50]")
        return False

    except TimeoutException:
        # If the check for the profile summary container TIMED OUT, it means
        # we are on the "People" tab but the content isn't there yet.
        # THIS IS THE DEFINITION OF THE LOADING STATE.
        log("[cyan]Profile content not found. App is currently in a loading state.[/cyan]")
        return True
    
    except Exception as e:
        # Any other error means something is wrong, so we are not loading.
        log(f"[red]An unexpected error occurred while checking loading state: {e}[/red]")
        return False

def is_out_of_likes_popup_present(driver, timeout_sec=2):
    """
    Checks if the "You're all out of likes" popup is currently visible on the screen.

    This function attempts to find the unique header text of the popup. It uses a short
    timeout because the popup should either be present immediately or not at all.

    Args:
        driver: The Appium WebDriver instance.
        timeout_sec (int): The maximum number of seconds to wait for the popup to be detected.

    Returns:
        bool: True if the "out of likes" popup is found, False otherwise.
    """
    try:
        # Use WebDriverWait to look for the element for a short duration.
        # If the element is found within the timeout, the function proceeds.
        WebDriverWait(driver, timeout_sec).until(
            EC.presence_of_element_located(OUT_OF_LIKES_HEADER_LOCATOR)
        )
        log("[bold magenta]Detected 'Out of Likes' popup.[/bold magenta]")
        return True
    except TimeoutException:
        # This is the expected outcome when the popup is not present.
        # It's not an error, so we just return False.
        log("[green]No 'Out of Likes' popup found. Proceeding normally.[/green]")
        return False
    except Exception as e:
        # Catch any other unexpected errors during the check.
        log(f"[red]An unexpected error occurred while checking for the 'Out of Likes' popup: {e}[/red]")
        return False

def wait_for_profile_to_load(driver, load_timeout_sec=1.0):
    """
    Checks if a profile card is currently loaded and ready on the screen.
    This function performs a SINGLE check without retries.

    It verifies two conditions:
    1. The "People" tab is selected in the navigation bar.
    2. The main scrollable profile container is present.

    Args:
        driver: The Appium WebDriver instance.
        load_timeout_sec (float): How long to wait for the elements to appear.

    Returns:
        bool: True if a profile is loaded, False otherwise.
    """
    try:
        # Check 1: A very fast check to ensure we're on the right screen.
        WebDriverWait(driver, 0.2).until(
            EC.presence_of_element_located(SELECTED_PEOPLE_TAB_LOCATOR)
        )

        # Check 2: The main check for the profile content itself.
        WebDriverWait(driver, load_timeout_sec).until(
            EC.presence_of_element_located(PROFILE_SCROLL_CONTAINER_LOCATOR)
        )

        # If both checks pass, the profile is considered loaded.
        return True

    except TimeoutException:
        # This is the expected, normal result when a profile isn't loaded.
        return False
    
    except Exception as e:
        # Catch any other unexpected errors during the check.
        log(f"[red]Unexpected error while checking for profile load: {e}[/red]")
        return False

def handle_best_photo_popup(driver, timeout=3):
    """
    Checks for the "Best Photo" feature popup and clicks "Save and close".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the popup was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the popup.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(BEST_PHOTO_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        log("[yellow]'Best Photo' popup detected ('Put your best photo first').[/yellow]")

        # 2. If the popup is detected, find and click the "Save and close" button.
        save_and_close_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(BEST_PHOTO_POPUP_SAVE_AND_CLOSE_BUTTON_LOCATOR)
        )
        
        action_delay = random.uniform(0.4, 0.8)
        log(f"[yellow]Clicking 'Save and close' button in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        save_and_close_button.click()
        log("[green]Clicked 'Save and close' on the 'Best Photo' popup.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss and settle
        return True # Popup was handled

    except TimeoutException:
        # The popup was not found within the timeout period. This is normal.
        # log("[grey50]Debug: 'Best Photo' popup not found.[/grey50]")
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling the 'Best Photo' popup: {e}[/red]")
        # try:
        #     log(f"[grey37]Page source on 'Best Photo' popup error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False


def handle_they_saw_you_premium_popup(driver, timeout=1):
    """
    Checks for the "They saw you, they're into you" Premium upsell popup
    and clicks "Maybe later".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the ad was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of a distinctive element of the ad.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(THEY_SAW_YOU_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        log("[yellow]'They saw you, they're into you' Premium popup detected.[/yellow]")

        # 2. If the ad is detected, try to click the "Maybe later" button.
        try:
            maybe_later_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(THEY_SAW_YOU_POPUP_MAYBE_LATER_BUTTON_LOCATOR)
            )
            
            action_delay = random.uniform(0.3, 0.6)
            log(f"[yellow]Clicking 'Maybe later' in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            
            maybe_later_button.click()
            log("[green]Clicked 'Maybe later' on 'They saw you' Premium popup.[/green]")

        except TimeoutException:
            log("[yellow]'Maybe later' button not found or clickable. Trying 'Close' button as fallback...[/yellow]")
            # Fallback to the "Close" button (top left)
            # Ensure THEY_SAW_YOU_POPUP_CLOSE_BUTTON_LOCATOR is accurate for this specific popup's close button.
            # The XML structure for the close button is: clickable View -> (View content-desc="Close", Button)
            # We target the clickable View that contains the "Close" element.
            # Let's refine the close button XPath for this specific structure:
            actual_close_button_locator = (AppiumBy.XPATH, "//android.view.View[@clickable='true' and .//android.view.View[@content-desc='Close']]")
            # This looks for a clickable View that has a descendant View with content-desc="Close".

            close_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(actual_close_button_locator)
            )
            action_delay = random.uniform(0.4, 1.1)
            log(f"[yellow]Clicking top 'Close' button in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            close_button.click()
            log("[green]Clicked top 'Close' button on 'They saw you' Premium popup.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss the popup and settle
        
        return True # Ad was handled

    except TimeoutException:
        # The ad was not found within the timeout period. This is normal.
        # log("[grey50]Debug: 'They saw you' Premium popup not found.[/grey50]")
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling the 'They saw you' Premium popup: {e}[/red]")
        # try:
        #     log(f"[grey37]Page source on 'They saw you' error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False



def handle_its_a_match_and_opening_moves_popup(driver, timeout=1,fallback_to_close=True):
    """
    Checks for the "It's a Match!" screen. If found:
    1. Handles the "Opening Moves" info box (if present).
    2. Types "hi" into the mini composer and sends it.
    3. Navigates back (e.g., to swiping).

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for elements.
        fallback_to_close (bool): If True, attempts to close the match screen if sending "hi" fails.

    Returns:
        bool: True if the "It's a Match!" screen was detected and an action (send or close) was performed, False otherwise.
    """
    try:
        # 1. Check for the main "It's a Match!" screen.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(ITS_A_MATCH_SCREEN_IDENTIFIER_TEXT)
        )
        log("[yellow]'It's a Match!' screen detected.[/yellow]")
        
        action_taken_on_match_screen = False # Flag to track if we did anything

        # 2. (Optional) Try to click "Got it" for the "Opening Moves" info box if it's present.
        chance = random.uniform(0,10)
        if chance > 6:
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located(OPENING_MOVES_INFO_BOX_TEXT_LOCATOR)
                )
                opening_moves_got_it_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable(OPENING_MOVES_INFO_BOX_GOT_IT_BUTTON_LOCATOR)
                )
                log(f"[yellow]Found 'Opening Moves' info box. Clicking 'Got it'...")
                opening_moves_got_it_button.click()
                log("[green]Clicked 'Got it' on 'Opening Moves' info box.[/green]")
                time.sleep(random.uniform(0.5, 1.0)) # Pause after this click
                action_taken_on_match_screen = True
            except TimeoutException:
                log("[grey50]Debug: 'Opening Moves' info box not found on 'It's a Match!' screen. Skipping its 'Got it'.[/grey50]")
            except Exception as e_om:
                log(f"[orange_red1]Minor error handling 'Opening Moves' info box: {e_om}. Proceeding.[/orange_red1]")

            # 3. Type "hi" into the mini composer and send.
            message_sent_successfully = False
            try:
                log("[yellow]Attempting to send message from 'It's a Match!' screen...[/yellow]")
                mini_composer_input = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable(MATCH_SCREEN_MINI_COMPOSER_INPUT_LOCATOR)
                )
                
                mini_composer_input.click() # Focus the input
                time.sleep(0.3)
                
                # Clear if needed (e.g., if "Send a message..." is actual text, not just hint)
                if mini_composer_input.text.lower() == "send a message...":
                     mini_composer_input.clear()
                     time.sleep(0.2)

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
                message_to_send = random.choice(opening_lines )
                mini_composer_input.send_keys(message_to_send)
                log(f"[green]Typed '{message_to_send}' into mini composer.[/green]")
                time.sleep(random.uniform(0.5, 1.0)) # Pause after typing

                # The send icon becomes enabled after typing.
                send_icon = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable(MATCH_SCREEN_MINI_COMPOSER_SEND_ICON_LOCATOR)
                )
                # Double check if it's actually enabled, though element_to_be_clickable should cover this
                if not send_icon.is_enabled():
                    log("[orange_red1]Send icon found but reported as not enabled. Attempting click anyway.[/orange_red1]")
                    # This might indicate an issue or a slight delay in UI update for enabled state.

                send_icon.click()
                log("[green]Clicked send icon.[/green]")
                message_sent_successfully = True
                action_taken_on_match_screen = True
                time.sleep(random.uniform(0.5, 1.0)) # Pause after sending


            except TimeoutException:
                log("[red]Failed to find mini composer elements or send message on 'It's a Match!' screen.[/red]")
            except Exception as e_send:
                log(f"[red]Error sending message from 'It's a Match!' screen: {e_send}[/red]")

            # 4. If sending "hi" failed AND fallback is enabled, try to close the screen.
            #    Or, if you ALWAYS want to close after sending, this logic changes.
            #    Current logic: Prioritize sending message. If that path fails, then consider closing.
            if not message_sent_successfully and fallback_to_close:
                log("[yellow]Sending 'hi' failed or was skipped. Attempting to close 'It's a Match!' screen as fallback.[/yellow]")
                try:
                    main_close_button = WebDriverWait(driver, 2).until( # Shorter timeout for fallback close
                        EC.element_to_be_clickable(ITS_A_MATCH_MAIN_CLOSE_BUTTON_LOCATOR)
                    )
                    main_close_button.click()
                    log("[green]Clicked main 'Close' button to dismiss 'It's a Match!' screen (fallback).[/green]")
                    action_taken_on_match_screen = True
                    time.sleep(random.uniform(1.2, 2.2))
                except Exception as e_close:
                    log(f"[red]Failed to close 'It's a Match!' screen via 'Close' button during fallback: {e_close}[/red]")
                    log("[orange_red1]Attempting system back as final fallback for 'It's a Match!' screen.[/orange_red1]")
                    time.sleep(1.5)
                    action_taken_on_match_screen = True # Assume back action did something

            elif message_sent_successfully:
                # If message was sent, we still need to get off this screen.
                # Typically, after sending from this mini-composer, the screen might auto-dismiss
                # or transition to the full chat. If it just stays on "It's a Match!", we need to close it.
                log("[grey50]Message sent from 'It's a Match!'. Performing system back to return to swiping.[/grey50]")
                time.sleep(random.uniform(0.3, 1.0))
                action_taken_on_match_screen = True


            return True
        else:
            try:
                main_close_button = WebDriverWait(driver, 2).until( # Shorter timeout for fallback close
                    EC.element_to_be_clickable(ITS_A_MATCH_MAIN_CLOSE_BUTTON_LOCATOR)
                )
                main_close_button.click()
                log("[green]Clicked main 'Close' button to dismiss 'It's a Match!' screen (fallback).[/green]")
                action_taken_on_match_screen = True
                time.sleep(random.uniform(1.2, 2.2))
            except Exception as e_close:
                log(f"[red]Failed to close 'It's a Match!' screen via 'Close' button during fallback: {e_close}[/red]")
                log("[orange_red1]Attempting system back as final fallback for 'It's a Match!' screen.[/orange_red1]")
                time.sleep(1.5)
                action_taken_on_match_screen = True # Assume back action did something
            log("[green]Nah Im Skipping This One.[/green]")
    except TimeoutException:
        # The "It's a Match!" screen itself was not found.
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling the 'It's a Match!' screen: {e}[/red]")
        return False

def handle_first_move_info_screen(driver, timeout=1):

    """
    Checks for the "It's time to make your move" info screen and clicks the "Close" button.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the screen elements.

    Returns:
        bool: True if the screen was detected and "Close" was clicked, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the screen.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(FIRST_MOVE_SCREEN_IDENTIFIER_TEXT_LOCATOR)
        )
        log("[yellow]'First Move' info screen detected ('It's time to make your move').[/yellow]")

        # 2. If the screen is detected, find and click the "Close" button.
        close_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(FIRST_MOVE_SCREEN_CLOSE_BUTTON_LOCATOR)
        )
        
        action_delay = random.uniform(0.2, 0.6)
        log(f"[yellow]Clicking 'Close' button on 'First Move' info screen in {action_delay:.2f} seconds...[/yellow]")
        time.sleep(action_delay)
        
        close_button.click()
        log("[green]Clicked 'Close' on the 'First Move' info screen.[/green]")
        
        # Add a pause after clicking to allow the UI to dismiss and settle
        
        return True # Screen was handled

    except TimeoutException:
        # The screen was not found within the timeout period. This is normal.
        # log("[grey50]Debug: 'First Move' info screen not found.[/grey50]")
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling the 'First Move' info screen: {e}[/red]")
        # try:
        #     log(f"[grey37]Page source on 'First Move' info screen error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False


def handle_superswipe_info_popup(driver, timeout=1):
    """
    Checks for the "SuperSwipe info/upsell" popup and clicks "Got it".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the popup was detected and handled, False otherwise.
    """
    try:
        # 1. Check for the presence of the identifying text of the popup.
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(SUPERSWIPE_POPUP_IDENTIFIER_TEXT_LOCATOR)
        )
        log("[yellow]SuperSwipe info/upsell popup detected ('Supercharge your chance to match').[/yellow]")

        # 2. If the popup is detected, find and click the "Got it" button.
        #    We could also try the "Close" button if "Got it" fails, but "Got it" is usually the primary dismissal.
        try:
            got_it_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(SUPERSWIPE_POPUP_GOT_IT_BUTTON_LOCATOR)
            )
            
            action_delay = random.uniform(0.2, 0.6)
            log(f"[yellow]Clicking 'Got it' in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            
            got_it_button.click()
            log("[green]Clicked 'Got it' on the SuperSwipe info popup.[/green]")

        except TimeoutException:
            log("[yellow]'Got it' button not immediately found or clickable. Trying 'Close' button as fallback...[/yellow]")
            # Fallback to the "Close" button if "Got it" is not found/clickable
            close_button = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable(SUPERSWIPE_POPUP_CLOSE_BUTTON_LOCATOR)
            )
            action_delay = random.uniform(0.4, 1.1)
            log(f"[yellow]Clicking 'Close' button in {action_delay:.2f} seconds...[/yellow]")
            time.sleep(action_delay)
            close_button.click()
            log("[green]Clicked 'Close' button on the SuperSwipe info popup.[/green]")
            
        # Add a pause after clicking to allow the UI to dismiss the popup and settle
        
        return True # Popup was handled

    except TimeoutException:
        # The popup was not found within the timeout period. This is normal.
        # log("[grey50]Debug: SuperSwipe info popup not found.[/grey50]")
        return False
    except Exception as e:
        log(f"[red]An error occurred while handling the SuperSwipe info popup: {e}[/red]")
        # try:
        #     log(f"[grey37]Page source on SuperSwipe info error:\n{driver.page_source[:2000]}[/grey37]")
        # except: pass
        return False
def handle_premium_ad_popup(driver, timeout=1):
    """
    Checks for the "Premium" upsell ad popup and clicks "Maybe later".

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup elements.

    Returns:
        bool: True if the ad was detected and handled, False otherwise.
    """
    try:
        maybe_later_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(PREMIUM_AD_MAYBE_LATER_BUTTON_LOCATOR)
        )
        action_delay = random.uniform(0.2, 0.5)
        log(f"[yellow]Premium ad detected. Clicking in {action_delay:.2f}s...[/yellow]")
        time.sleep(action_delay)
        maybe_later_button.click()
        return True
    except TimeoutException:
        return False
    except Exception as e:
        log(f"[red]Error in premium ad handler: {e}[/red]")
        return False

def is_popup_present(driver):
    popup = driver.find_elements(AppiumBy.XPATH, "//android.view.ViewGroup/android.view.View/android.view.View/android.view.View")
    return len(popup) > 0

def handle_interested_confirmation_popup(driver, timeout=1):
    """
    Checks for the "Interested?" confirmation popup and clicks "YES".
    This popup typically appears to confirm a right swipe action.

    Args:
        driver: The Appium WebDriver instance.
        timeout (int): Maximum time to wait for the popup to appear.

    Returns:
        bool: True if the popup was detected and "YES" was clicked, False otherwise.
    """
    # Locators based on the provided XML for the "Interested?" popup
    popup_panel_locator = (AppiumBy.ID, "com.bumble.app:id/parentPanel") # Main dialog panel
    yes_button_locator = (AppiumBy.ID, "android:id/button1") # Standard Android dialog "positive" button ID
    # More specific XPath for YES button if needed:
    # yes_button_locator_xpath = (AppیمBy.XPATH, "//android.widget.Button[@resource-id='android:id/button1' and @text='YES']")

    try:
        yes_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((AppiumBy.ID, "android:id/button1"))
        )
        action_delay = random.uniform(0.2, 0.4)
        log(f"[yellow]Popup 'Interested?' detected. Clicking YES in {action_delay:.2f}s...[/yellow]")
        time.sleep(action_delay)
        yes_button.click()
        return True
    except TimeoutException:
        return False
    except Exception as e:
        log(f"[red]Error in 'Interested?' handler: {e}[/red]")
        return False


def vertical_scroll(driver, is_first_swipe=False):
    """
    Perform a vertical scroll to check profile details.
    
    Args:
        driver: Appium WebDriver instance
        is_first_swipe: If True, performs a longer initial scroll
    """
    # Reduced delay before vertical scroll (0.2-0.8 seconds)
    # time.sleep(random.uniform(0.2, 0.8))
    screen_width, screen_height = get_screen_dimensions(driver)
    if not screen_width or not screen_height:
        log("[red]Failed to get screen dimensions for vertical scroll. Aborting scroll.[/red]")
        return
    # Perform vertical scroll with increased range
    start_y = int(screen_height * random.uniform(0.50, 0.70))
    
    # Longer scroll for first swipe
    if is_first_swipe:
        scroll_distance = int(screen_height * random.uniform(0.40, 0.55))
    else:
        scroll_distance = int(screen_height * random.uniform(0.30, 0.45))
    end_y = start_y - scroll_distance
    
    # Ensure end_y is not negative (scrolling off the top)
    end_y = max(50, end_y) # Keep at least 50px from top

    # Start X: somewhere in the middle 30% to 70% of screen width
    start_x = int(screen_width * random.uniform(0.30, 0.70))
    
    log(f"[grey50]Vertical scroll: screen_h={screen_height}, start_y={start_y}, end_y={end_y}, start_x={start_x}[/grey50]")

    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    time.sleep(random.uniform(0.05, 0.15)) # Brief pause before action
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    num_points = random.randint(2, 4) # More intermediate points for smoother scroll
    duration_ms = random.randint(300, 600) # Total scroll duration in ms
    
    for i in range(num_points):
        progress = (i + 1) / num_points
        current_y = int(start_y + (end_y - start_y) * progress)
        # Slight horizontal variance during scroll
        current_x = int(start_x + random.randint(-int(screen_width*0.02), int(screen_width*0.02))) 
        current_x = max(0, min(screen_width -1, current_x)) # Boundary check for x

        actions.w3c_actions.pointer_action.move_to_location(current_x, current_y)
        # time.sleep per point can be derived from total duration
        time.sleep((duration_ms / 1000.0) / num_points * random.uniform(0.8, 1.2)) 
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, end_y) # Ensure final point is reached
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    log(f"[grey50]Vertical scroll performed from ({start_x},{start_y}) to ({start_x},{end_y}).[/grey50]")

def horizontal_swipe(driver, swipe_right=True):
    """
    Perform a single horizontal swipe, aiming for a faster, more decisive gesture.
    """
    screen_width, screen_height = get_screen_dimensions(driver)
    if not screen_width or not screen_height:
        log("[red]Failed to get screen dimensions for horizontal swipe. Aborting swipe.[/red]")
        return

    # Start Y: Middle portion of the screen, slightly more constrained.
    start_y_percentage = random.uniform(0.40, 0.60) # Centered vertically more
    start_y = int(screen_height * start_y_percentage)
    
    # Swipe distance: Keep it substantial (55% to 70% of screen width).
    # Slightly reduced the upper bound a bit from 75% to 70% to prevent overshooting if screen is small,
    # but the key is the speed and decisiveness.
    swipe_distance_percentage = random.uniform(0.55, 0.70) 
    swipe_distance = int(screen_width * swipe_distance_percentage)

    if swipe_right:
        # Start X: From left part of the screen (e.g., 15% to 25%) - start a bit more inwards
        start_x_percentage = random.uniform(0.15, 0.25)
        start_x = int(screen_width * start_x_percentage)
        end_x = start_x + swipe_distance
    else: # swipe_left
        # Start X: From right part of the screen (e.g., 75% to 85%) - start a bit more inwards
        start_x_percentage = random.uniform(0.75, 0.85)
        start_x = int(screen_width * start_x_percentage)
        end_x = start_x - swipe_distance

    # Ensure end_x stays well within screen bounds with a slightly larger margin
    end_x = max(int(screen_width * 0.08), min(int(screen_width * 0.92), end_x)) # 8% margin

    # Vertical variation at the end of the swipe - keep it moderate
    end_y_variation_percentage = random.uniform(-0.06, 0.06) # +/- 6% of screen height
    end_y = start_y + int(screen_height * end_y_variation_percentage)
    end_y = max(int(screen_height*0.20), min(int(screen_height*0.80), end_y)) # Keep Y within 20-80% to avoid edges
    
    log(f"[grey50]Horizontal swipe: screen_w={screen_width}, start_x={start_x} ({start_x_percentage*100:.1f}%), end_x={end_x}, dist_perc={swipe_distance_percentage*100:.1f}%[/grey50]")

    actions = ActionChains(driver)
    actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
    
    # Very minimal pause before action starts
    time.sleep(random.uniform(0.01, 0.05)) 
    
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    
    # --- Adjusting for speed and decisiveness ---
    # Fewer intermediate points, faster total duration for a "quicker flick"
    num_points = random.randint(2, 4) 
    duration_ms = random.randint(150, 350) # Target total swipe duration in ms (FASTER)

    # Create a list of points including the start and end
    points = [(start_x, start_y)]
    for i in range(1, num_points + 1):
        progress = i / (num_points + 1.0) # Ensure progress goes towards end point
        
        # For a more "natural" arc or fling, the intermediate points shouldn't be perfectly linear.
        # We can make the x-component progress faster initially or towards the end for a fling.
        # Simple approach: slightly accelerate progress for x
        fling_progress_x = progress ** 0.8 # Makes it move a bit faster initially on x-axis
        
        current_x = int(start_x + (end_x - start_x) * fling_progress_x)
        current_y = int(start_y + (end_y - start_y) * progress) # Y can move more linearly

        # Add less random jitter if we want a more direct, fast swipe
        current_x += random.randint(-int(screen_width*0.01), int(screen_width*0.01))
        current_y += random.randint(-int(screen_height*0.01), int(screen_height*0.01))
        
        current_x = max(0, min(screen_width -1, current_x))
        current_y = max(0, min(screen_height -1, current_y))
        points.append((current_x, current_y))
    
    # Add the final precise end point
    if points[-1] != (end_x, end_y): # Ensure the last point is the target
        points.append((end_x, end_y))

    # Perform the moves
    for k in range(1, len(points)): # Start from the second point in our list
        px, py = points[k]
        # The duration of each segment of the move
        segment_duration_s = (duration_ms / 1000.0) / (len(points)-1) 
        actions.w3c_actions.pointer_action.move_to_location(px, py)
        time.sleep(segment_duration_s * random.uniform(0.8, 1.2)) # Slight variation in segment timing
    
    # No need for an extra move_to_location if the loop handles the last point correctly.
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    
    swipe_dir = "RIGHT" if swipe_right else "LEFT"
    log(f"[grey50]Horizontal swipe {swipe_dir} performed (duration: ~{duration_ms}ms).[/grey50]")
    time.sleep(random.uniform(0.1, 0.3)) # Reduced pause after swipe from 0.2-0.6 to 0.1-0.3ndle 
def realistic_swipe(driver, right_swipe_probability=5, duration_minutes=5,logger_func: logging.Logger = rprint):
    """
    Perform realistic swipes on Bumble with profile checking behavior.
    
    Args:
        driver: Appium WebDriver instance
        right_swipe_probability: Probability of swiping right (0-10)
        duration_minutes: How long to run the swiping session
    """
    global log
    log = logger_func
    end_time = time.time() + (duration_minutes * 60)
    
    while time.time() < end_time:
        # Random delay between profiles (2-3 seconds)
        loading_start_time = time.time()

        current_app = driver.current_package
        log("[green]The current package:",current_package)
        if current_app != "com.instagram.android":
            log("[bold red]The app just closed![/bold red]")
            return

        if not wait_for_profile_to_load(driver, load_timeout_sec=1.0):

            log("[yellow]Profiles are not loading. Doing a few checks[/yellow]")
            start_time = time.time()
            if handle_adjust_filters_prompt(driver,0): # Uses internal timeout
                log(f"[grey50]Time taken for adjust filters prompt check: {time.time() - start_time:.3f} seconds[/grey50]")
                log("[yellow]'Adjust filters' prompt appeared. Attempting to modify filters.[/yellow]")
                if adjust_age_filter_and_apply(driver): # Uses internal timeout
                    log("[green]Age filter adjusted. Continuing swipe session.[/green]")
                    time.sleep(random.uniform(1.0, 2.0)) # Pause for UI to settle
                else:
                    log("[red]Failed to adjust age filter. Stopping swipe session.[/red]")
                    return # Critical failure
                continue # Restart loop

            start_time = time.time()
            if handle_its_a_match_and_opening_moves_popup(driver,0):
                continue 
            log(f"[grey50]Time taken for its a match popup check: {time.time() - start_time:.3f} seconds[/grey50]")

            # 3. "Out of likes" or other critical blocking popups
            # IMPORTANT: Ensure is_popup_present uses SPECIFIC locators for the "out of likes" popup.

            start_time = time.time()
            if is_popup_present(driver): 
                log("[green]Popup detected![/green]")

                if handle_interested_confirmation_popup(driver,0):
                    log("[green]Handled 'Interested?' popup. Moving to next profile cycle.[/green]")
                    time.sleep(random.uniform(0.5, 1.5)) # Pause after handling
                    continue # Restart loop for the next profile evaluation

                log(f"[grey50]Time taken for interested confirmation popup check: {time.time() - start_time:.3f} seconds[/grey50]")
                # 2. Handle "Premium Ad" Popup (NEW)
                start_time = time.time()
                if handle_premium_ad_popup(driver,0): # Call the new handler
                    # Log already in handle_premium_ad_popup
                    # This popup usually dismisses to continue swiping, so we 'continue' the loop.
                    continue
                log(f"[grey50]Time taken for premium ad popup check: {time.time() - start_time:.3f} seconds[/grey50]")

                start_time = time.time()
                if handle_superswipe_info_popup(driver,0): # Call the new handler
                    # This popup usually dismisses to continue swiping.
                    continue
                log(f"[grey50]Time taken for superswipe info popup check: {time.time() - start_time:.3f} seconds[/grey50]")

                start_time = time.time()
                if handle_first_move_info_screen(driver,0):
                    # This screen dismissal usually returns to swiping.
                    continue
                
                log(f"[grey50]Time taken for first move info screen check: {time.time() - start_time:.3f} seconds[/grey50]")

                # if handle_they_saw_you_premium_popup(driver):
                #     # This popup dismissal should return to swiping.
                #     continue

                start_time = time.time()
                if handle_first_move_info_screen(driver,0):
                    # This screen dismissal usually returns to swiping.
                    continue
                
                log(f"[grey50]Time taken for second first move info screen check: {time.time() - start_time:.3f} seconds[/grey50]")

                start_time = time.time()
                if handle_best_photo_popup(driver, timeout=0):
                    continue

                log(f"[grey50]Time taken for best photo popup screen check: {time.time() - start_time:.3f} seconds[/grey50]")
                if is_out_of_likes_popup_present(driver,0):
                    log("[red]Out of likes :([/red]")
                    log("[red]Aborting Swipe Because We Are Out Of Likes([/red]")
                    driver.back()
                    return
                # Press the popup button blindly
                actions = ActionChains(driver)
                actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
                actions.w3c_actions.pointer_action.move_to_location(350, 1307)
                actions.w3c_actions.pointer_action.pointer_down()
                actions.w3c_actions.pointer_action.pause(0.2)
                actions.w3c_actions.pointer_action.release()
                actions.perform()

                log(f"[grey50]Time taken for critical popup check: {time.time() - start_time:.3f} seconds[/grey50]")
                if not wait_for_profile_to_load(driver, load_timeout_sec=2.0):
                    driver.back()
                if not wait_for_profile_to_load(driver, load_timeout_sec=2.0):
                    log("[red]Critical popup (likely 'Out of likes') detected by is_popup_present. Stopping swipe session.[/red]")
                    return # Stop swiping
                else:
                    continue
            # if not popup check if its loading
            if is_profile_loading(driver,timeout_sec=1.0):
                log(f"[grey50]The Page is Loading! lets Sleep for 4 sec and try again.[/grey50]")
                max_retries = 5
                wait_per_retry_sec = 4.0
                profile_is_loaded = False

                for attempt in range(max_retries):
                    time.sleep(wait_per_retry_sec)
                    if not is_profile_loading(driver,timeout_sec=1.0):
                        log(f"[green]The Page Loaded![/green]")
                        profile_is_loaded = True
                        break
                if not profile_is_loaded:
                    log("[red]Stuck on Loading. Stopping swipe session.[/red]")
                    return # Stop swiping
                else:continue
            else:
                log("[red]Unhandled Page Showed up![/red]")
                log("[red]Restarting the app...[/red]")
                driver.terminate_app("com.bumble.app")
                time.sleep(2)
                driver.activate_app("com.bumble.app")
                time.sleep(3)
                if not wait_for_profile_to_load(driver,load_timeout_sec=1) and not is_popup_present(driver,load_timeout_sec=1) and not is_profile_loading(driver,load_timeout_sec=1):
                    log("[red]The Account required Verification or Banned![/red]")
                    log("[red]Terminating Swipe process![/red]")
                    return
                else:
                    continue



        log(f"[green]Time taken for Profile to load: {time.time() - loading_start_time:.3f} seconds[/green]")
        time.sleep(random.uniform(0, 2))
        
        # 60% chance to check profile details
        if random.randint(1, 10) <= 6:
            # Random number of vertical scrolls (2-4)
            num_scrolls = random.randint(2, 4)
            
            for i in range(num_scrolls):
                # First swipe is longer
                vertical_scroll(driver, is_first_swipe=(i == 0))
        
        # Perform horizontal swipe
        swipe_right = random.randint(1, 10) <= right_swipe_probability
        horizontal_swipe(driver, swipe_right)

if __name__ == "__main__":
    # Test configuration
    from appium import webdriver
    from appium.webdriver.common.appiumby import AppiumBy
    from appium.options.android import UiAutomator2Options
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.platform_version = "13"
    options.device_name = "RZ8W90Q3Q2A"
    options.automation_name = "UiAutomator2"
    options.app_package = "com.bumble.app"
    # options.app_activity = "com.bumble.app.ui.screenstories.ScreenStoryBlockersActivity"
    options.no_reset = True
    options.uiautomator2_server_install_timeout = 220000
    
    APPIUM_SERVER_URL = "http://127.0.0.1:4723"
    # Your Appium server configuration
    try:
        # Initialize the driver
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        
        # Wait for app to load
        time.sleep(5)
        
        log("[yellow]Testing vertical scroll...[/yellow]")
        # Test vertical scroll
        vertical_scroll(driver, is_first_swipe=True)  # Test first swipe
        time.sleep(2)
        vertical_scroll(driver, is_first_swipe=False)  # Test normal swipe
        time.sleep(2)
        
        log("[yellow]Testing horizontal swipes...[/yellow]")
        # Test horizontal swipes
        horizontal_swipe(driver, swipe_right=True)  # Test right swipe
        time.sleep(2)
        horizontal_swipe(driver, swipe_right=False)  # Test left swipe
        
        log("[green]Tests completed successfully![/green]")
        
    except Exception as e:
        log(f"[red]An error occurred: {str(e)}[/red]")
    
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()
