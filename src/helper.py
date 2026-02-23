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
    "PROFILE": "com.instagram.android:id/profile_tab",
}


# --- HELPER: POPUP HANDLING ---
def handle_common_popups(driver):
    """
    Checks for and closes common Instagram interruptions.
    """
    dismiss_texts = [
        "Not now",
        "Cancel",
        "Deny",
        "Don't Allow",
        "No, thanks",
        "Later",
        "Dismiss",
        "Got it",
        "No",
        "Leave",
    ]
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
        if driver(
            resourceId="com.instagram.android:id/edit_name_and_bio_description"
        ).exists(timeout=1):
            return "PROFILE_SCREEN"

        # Search specific: Search input
        if driver(
            resourceId="com.instagram.android:id/action_bar_search_edit_text"
        ).exists(timeout=1):
            return "SEARCH_SCREEN"

    except:
        pass

    return "UNKNOWN_SCREEN"


def is_account_banned_or_checkpoint(driver):
    """
    Checks for the 'Confirm you're human' or 'Verify your account' screens.
    Returns True if the account is stuck/banned.
    """
    # 1. Check for the specific text from your XML
    # "Confirm you're human to use your account..."
    ban_indicators = [
        "Confirm you're human",
        "Help us confirm",
        "Suspended",
        "Verify your account",
    ]

    for text_val in ban_indicators:
        if driver(textContains=text_val).exists(timeout=1):
            return True

    # 2. Check for the 'Continue' button seen in your XML
    if (
        driver(description="Continue").exists(timeout=0.5)
        and not driver(resourceId=NAV_BAR_ID).exists()
    ):
        return True

    return False


def open_page(
    driver,
    page_name_from_ui,
    navigation_timeout=5,
    verification_timeout=3,
    logger_func=rprint,
):
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
        log(f"[yellow]Navigating to {target_key}...[/yellow]")
        tab = driver(resourceId=target_id)

        # 1. OPTIMISTIC CLICK
        if tab.exists(timeout=1.5):
            tab.click()
        else:
            # Check for ban if tab bar is missing
            if is_account_banned_or_checkpoint(driver):
                log("[bold red]!!! ACCOUNT BANNED / CHECKPOINT DETECTED !!![/bold red]")
                raise Exception("ACCOUNT_BANNED")

            log("[dim]Tab bar not found, clearing popups...[/dim]")
            handle_common_popups(driver)

            # Click with a slight wait
            if not tab.click(timeout=3):
                log(f"[red]Could not find {target_key} tab after popups.[/red]")
                # Fall through to recovery
            else:
                # Small sleep to let IG flip the 'selected' attribute
                time.sleep(0.5)

        # 2. ROBUST VERIFICATION (Avoids RPC -32002)
        # We wait for the ID to exist first
        if tab.wait(timeout=verification_timeout):
            # Then we check if it is selected via .info (This is safer than putting it in the selector)
            if tab.info.get("selected"):
                log(f"[green]Successfully on {target_key}.[/green]")
                return True

        # 3. FALLBACK VERIFICATION
        if get_current_screen_by_tab(driver, timeout=1) == target_screen_id:
            log(f"[green]Verification Success (Fallback) for {target_key}.[/green]")
            return True

        # 4. LAST RESORT: RECOVERY
        log(f"[red]Failed to verify {target_key}. Restarting app...[/red]")
        driver.app_stop(APP_PACKAGE)
        driver.app_start(APP_PACKAGE)
        time.sleep(2)
        return driver(resourceId=target_id).click(timeout=5)

    except Exception as e:
        err_msg = str(e).lower()

        # If it's a specific RPC Error, we treat it as a network hiccup to trigger Auto-Heal
        if "-32002" in err_msg:
            log("[yellow]Internal RPC Error (-32002). Triggering Auto-Heal...[/yellow]")
            raise e

        # Critical Network Errors
        critical_errors = [
            "rpc",
            "connection",
            "closed",
            "remote end",
            "offline",
            "timeout",
            "broken pipe",
        ]
        if any(x in err_msg for x in critical_errors):
            log(f"[red]Network Error in Nav: {e}[/red]")
            raise e

        # Custom Ban Error
        if "ACCOUNT_BANNED" in str(e):
            raise e

        log(f"[red]Logic Error in Nav: {e}[/red]")
        return False
