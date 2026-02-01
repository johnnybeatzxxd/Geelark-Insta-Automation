import time
import subprocess
from geelark_api import start_phone, get_phone_status, get_adb_information
from rich import print as rprint

def make_phone_ready(phone_id: str, launch_phone: bool = True) -> dict:
    """
    Makes a phone ready for use.
    - If launch_phone=True: Sends start command, updates DB stream URL, waits for boot.
    - If launch_phone=False: Checks status. If running, grabs ADB info immediately.
    
    Args:
        phone_id (str): The ID of the phone
        launch_phone (bool): Whether to send the start API command.
        
    Returns:
        dict: ADB connection info or {} if failed.
    """
    
    # --- PHASE 1: START OR CHECK ---
    if launch_phone:
        # A. Force Start
        start_response = start_phone([phone_id])
        rprint(f"Start Command Sent to: {phone_id}")
        
        if not start_response:
            rprint(f"[red]Failed to start phone {phone_id}[/red]")
            return {}
        
        # Save Stream URL to DB
        try:
            if isinstance(start_response, list) and len(start_response) > 0:
                url = start_response[0].get("url")
                if url:
                    from database import Account
                    Account.update(stream_url=url).where(Account.device_id == phone_id).execute()
                    rprint(f"[green]Stream URL saved for {phone_id}[/green]")
        except Exception as e:
            rprint(f"[red]Failed to save stream URL: {e}[/red]")
            
        rprint(f"[yellow]Starting phone {phone_id}...[/yellow]")
    
    else:
        # B. Check Status Only (Auto-Heal Mode)
        rprint(f"[dim]Checking status for {phone_id} (No Launch)...[/dim]")
        try:
            status_info = get_phone_status([phone_id])
            success_details = status_info.get("successDetails", [])
            
            if not success_details:
                rprint("[red]Could not verify phone status.[/red]")
                return {}
            
            status_code = success_details[0]["status"]
            
            if status_code == 2: # Shut down
                rprint(f"[red]Phone {phone_id} is OFF and launch_phone=False. Aborting.[/red]")
                return {}
            elif status_code == 3: # Expired
                rprint(f"[red]Phone {phone_id} is EXPIRED.[/red]")
                return {}
            elif status_code == 0: # Started
                rprint(f"[green]Phone {phone_id} is already running.[/green]")
                # We can grab existing stream url from DB just for logging/verification if needed
                # but no API call needed here.
        except Exception as e:
            rprint(f"[red]Status check failed: {e}[/red]")
            return {}

    # --- PHASE 2: WAIT FOR BOOT (Common) ---
    # We loop until status is 0 (Started). 
    # If launch_phone=False and it was already 0, this loop breaks instantly.
    
    rprint("[yellow]Waiting for phone availability...[/yellow]")
    
    max_wait_cycles = 20 # 5 minutes max
    cycle = 0
    
    while cycle < max_wait_cycles:
        # If we just checked status above and it was 0, we can optimize, 
        # but calling API again is safer to ensure it didn't crash in the last second.
        status_info = get_phone_status([phone_id])
        success_details = status_info.get("successDetails", [])
        
        if success_details:
            phone_status = success_details[0]
            code = phone_status["status"]
            
            if code == 0:  # Started
                # rprint(f"[green]Phone {phone_id} is active.[/green]")
                break
            elif code in [2, 3]: # Shut down / Expired
                rprint(f"[red]Phone died during boot (status: {code}).[/red]")
                return {}
        
        time.sleep(15)
        cycle += 1
    
    if cycle >= max_wait_cycles:
        rprint("[red]Timeout waiting for phone to start.[/red]")
        return {}

    # --- PHASE 3: GET ADB INFO ---
    adb_info = get_adb_information([phone_id])
    
    # Retry logic for ADB info
    if not adb_info or adb_info[0].get("code") != 0:
        rprint("[yellow]ADB not ready yet. Retrying...[/yellow]")
        time.sleep(5)
        adb_info = get_adb_information([phone_id])

    if not adb_info or adb_info[0].get("code") != 0:
        rprint("[red]Failed to get ADB information[/red]")
        return {}
        
    connection_info = adb_info[0]
    rprint(f"[cyan]ADB Ready: {connection_info['ip']}:{connection_info['port']}[/cyan]")
    return connection_info

def connect_to_phone(phone_id: str, launch_phone=True) -> dict:
    """
    Connects to a phone using ADB commands.
    First makes the phone ready, then establishes ADB connection and logs in.
    Will retry up to 3 times if connection fails.
    
    Args:
        phone_id (str): The ID of the phone to connect to
        
    Returns:
        dict: Connection information if successful, empty dict if failed
    """
    # First make sure the phone is ready
    connection_info = make_phone_ready(phone_id, launch_phone)
    if not connection_info:
        rprint("[red]Failed to get connection information[/red]")
        return {}
    
    # Construct the connection address
    connection_address = f"{connection_info['ip']}:{connection_info['port']}"
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Connect to the phone
            rprint(f"[yellow]Connecting to {connection_address}... (Attempt {retry_count + 1}/{max_retries})[/yellow]")
            connect_cmd = ["adb", "connect", connection_address]
            connect_result = subprocess.run(connect_cmd, capture_output=True, text=True)
            
            if "connected" in connect_result.stdout.lower():
                rprint("[green]Successfully connected to device[/green]")
                
                # Login to the phone
                rprint("[yellow]Logging in...[/yellow]")
                login_cmd = ["adb", "-s", connection_address, "shell", "glogin", connection_info['pwd']]
                login_result = subprocess.run(login_cmd, capture_output=True, text=True)
                
                if login_result.returncode == 0:
                    rprint("[green]Successfully logged in[/green]")
                    return connection_info
                else:
                    rprint(f"[red]Failed to login: {login_result.stderr}[/red]")
                    return {}
            else:
                rprint(f"[red]Failed to connect: {connect_result.stdout.rstrip()}[/red]")
                retry_count += 1
                if retry_count < max_retries:
                    rprint(f"[yellow]Retrying in 3 seconds...[/yellow]")
                    time.sleep(3)
                continue
                
        except subprocess.SubprocessError as e:
            rprint(f"[red]Error executing ADB commands: {str(e)}[/red]")
            retry_count += 1
            if retry_count < max_retries:
                rprint(f"[yellow]Retrying in 3 seconds...[/yellow]")
                time.sleep(3)
            continue
        except Exception as e:
            rprint(f"[red]Unexpected error: {str(e)}[/red]")
            return {}
    
    rprint("[red]Failed to connect after 3 attempts[/red]")
    return {}

if __name__ == "__main__":
    # Example usage
    
    phone_id = "569893771953571212"
    connection_info = connect_to_phone(phone_id)
    if connection_info:
        rprint("[green]Phone is ready for use![/green]")
    else:
        rprint("[red]Failed to connect to phone[/red]")
