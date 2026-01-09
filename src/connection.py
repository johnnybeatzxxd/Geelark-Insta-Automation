import time
import subprocess
from geelark_api import start_phone, get_phone_status, get_adb_information
from rich import print as rprint

def make_phone_ready(phone_id: str) -> dict:
    """
    Makes a phone ready for use by starting it and waiting for it to be fully started.
    Then retrieves and returns the ADB connection information.
    
    Args:
        phone_id (str): The ID of the phone to start
        
    Returns:
        dict: ADB connection information for the phone, or empty dict if failed
        
    Example return format:
    {
        "ip": str,        # Connection IP
        "port": str,      # Connection port
        "pwd": str        # Connection password
    }
    """
    # Start the phone
    start_response = start_phone([phone_id])
    print("this is start message")
    print(start_response)
    if not start_response:
        rprint(f"[red]Failed to start phone {phone_id}[/red]")
        return {}
    
    rprint(f"[yellow]Starting phone {phone_id}...[/yellow]")
    
    rprint("[yellow]Waiting for phone to start...[/yellow]")
    # Wait for phone to be fully started
    while True:
        status_info = get_phone_status([phone_id])
        
        # Check if we got any successful status information
        success_details = status_info.get("successDetails", [])
        if not success_details:
            rprint("[red]Failed to get phone status[/red]")
            return {}
            
        phone_status = success_details[0]
        
        # Status codes: 0=Started, 1=Starting, 2=Shut down, 3=Expired
        if phone_status["status"] == 0:  # Phone is started
            rprint(f"[green]Phone {phone_id} is now started[/green]")
            break
        elif phone_status["status"] in [2, 3]:  # Phone is shut down or expired
            rprint(f"[red]Phone {phone_id} is not available (status: {phone_status['status']})[/red]")
            return {}
            
        time.sleep(3)
    
    # Get ADB information
    adb_info = get_adb_information([phone_id])
    if not adb_info:
        rprint("[red]Failed to get ADB information[/red]")
        return {}
        
    # Check if we got valid ADB information
    if adb_info[0].get("code") != 0:
        rprint("[red]ADB information not ready yet[/red]")
        return {}
        
    connection_info = adb_info[0]
    rprint("\n[yellow]ADB Connection Information:[/yellow]")
    rprint(f"[cyan]IP: {connection_info['ip']}[/cyan]")
    rprint(f"[cyan]Port: {connection_info['port']}[/cyan]")
    rprint(f"[cyan]Password: {connection_info['pwd']}[/cyan]")
    
    return connection_info

def connect_to_phone(phone_id: str) -> dict:
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
    connection_info = make_phone_ready(phone_id)
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
