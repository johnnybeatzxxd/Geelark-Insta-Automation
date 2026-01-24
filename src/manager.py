import time
import multiprocessing
import datetime
from rich import print as rprint

# --- Import System Modules ---
import database as db
from services import run_automation_for_device, get_all_available_devices
from geelark_api import stop_phone

# --- CONFIGURATION ---
SESSION_CONFIG = {
    "batch_size": 100,           # Max targets given to a single worker run
    "session_limit_2h": 5,       # Max follows allowed before hard cooldown triggers
    "min_batch_start": 1,        # Min targets required to justify starting a worker
    "cooldown_hours": 2,         # Hard cooldown duration after completing a session
    "pattern_break": 4,
    "min_delay": 20,
    "max_delay": 45,
    "do_vetting": True,
}

# Tracks running Python processes: { "device_id": <Process Object> }
active_processes = {} 

def log(msg, style="white"):
    """Simple timestamped logger."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    rprint(f"[{timestamp}] [{style}]{msg}[/{style}]")

# --- COMMAND HELPERS ---

def kill_worker(device_id):
    """Safely terminates a specific worker process."""

    from database import Account, update_account_runtime_status
    if device_id in active_processes:
        proc = active_processes[device_id]
        if proc.is_alive():
            log(f"Executing KILL command for {device_id}...", "bold red")
            proc.terminate()
            proc.join(timeout=5)
        
        # Cleanup Memory
        del active_processes[device_id]
        
        # Cleanup DB (Release Targets)
        # We find targets currently reserved by this account
        try:
            from database import Account, Target, release_targets
            acc = Account.get(Account.device_id == device_id)
            reserved = Target.select().where((Target.status == 'reserved') & (Target.reserved_by == acc))
            users_to_free = [t.username for t in reserved]
            if users_to_free:
                log(f"Releasing {len(users_to_free)} targets for {device_id}.", "yellow")
                release_targets(users_to_free)
        except Exception as e:
            log(f"Error releasing targets during kill: {e}", "dim")

        # Cleanup Hardware
        log(f"Sending STOP signal to Cloud API for {device_id}...", "red")
        stop_phone([device_id])
        update_account_runtime_status(device_id, "DISABLED")
        return True
    return False

def process_command_queue():
    """Checks DB for instructions. Returns True if action was taken."""
    cmd = db.pop_pending_command() # Ensure this exists in database.py
    if not cmd: return False

    log(f"RECEIVED COMMAND: {cmd.command} (Target: {cmd.target_id})", "bold magenta")
    
    try:
        if cmd.command == "STOP_DEVICE":
            kill_worker(cmd.target_id)
            
        elif cmd.command == "STOP_ALL":
            log("STOP ALL command received. Killing all workers...", "bold red")
            for dev_id in list(active_processes.keys()):
                kill_worker(dev_id)
            # Optional: Turn off the Global Switch so it doesn't restart
            db.set_global_automation(False)

        db.complete_command(cmd.id, "completed") # Ensure this exists in database.py
        return True
        
    except Exception as e:
        log(f"Command Execution Failed: {e}", "red")
        db.complete_command(cmd.id, "failed")
        return False

def perform_startup_cloud_audit():
    """
    Ensures no phones are left running in the cloud 
    when the Manager starts fresh. Prevents ghost billing.
    """
    log("Starting Cloud Audit...", "bold cyan")
    try:
        live_devices = get_all_available_devices()
        zombie_ids = [d['id'] for d in live_devices if d.get('status') == 'active']
        
        if zombie_ids:
            log(f"FOUND {len(zombie_ids)} ZOMBIE PHONES ON CLOUD. Shutting them down...", "bold red")
            stop_phone(zombie_ids)
            log("Cloud state cleared.", "green")
        else:
            log("No zombie phones detected. Cloud is clean.", "dim")
            
        # Reset all runtime_statuses in DB to IDLE/STOPPED on startup
        from database import Account
        Account.update(runtime_status="READY").where(Account.status == 'active').execute()
        
    except Exception as e:
        log(f"Startup Audit Failed: {e}", "red")
def smart_sleep_and_listen(seconds):
    """
    Sleeps for X seconds, but checks for commands every 1 second.
    """
    for _ in range(seconds):
        if process_command_queue():
            # If we handled a command, we don't return immediately, 
            # we just keep sleeping to respect the cycle time, 
            # BUT we processed the command instantly.
            pass 
        time.sleep(1)

# --- MAIN LOOP ---
def manager_loop():
    log("FACTORY HEARTBEAT STARTED", "bold green")
    
    while True:
        # 0. Check Commands (Priority 1)
        process_command_queue()

        # 1. Global Switch Check
        if not db.is_automation_on():
            db.run_janitor_cleanup(timeout_minutes=30)
            if active_processes:
                log("Global Switch is OFF, but processes are active. INITIATING PURGE...", "bold red")
                running_ids = list(active_processes.keys())
                for dev_id in running_ids:
                    log(f"  -> Enforcing stop on {dev_id}...", "red")
                    kill_worker(dev_id)
                log("Purge complete. System is fully halted.", "green")
            
            # Even when paused, we update status to 'DISABLED' for UI feedback
            # (Optional: you can skip this if you want to keep last known state)
            smart_sleep_and_listen(5)
            continue

        # 2. Cleanup Finished Processes
        for dev_id, proc in list(active_processes.items()):
            if not proc.is_alive():
                log(f"Worker for {dev_id} finished naturally.", "blue")
                del active_processes[dev_id]

        # 3. Janitor Duty
        db.run_janitor_cleanup(timeout_minutes=30)

        # 4. AUTO-COMPLETE CHECK
        pending_targets = db.get_total_pending_targets()
        if pending_targets == 0 and len(active_processes) == 0:
            log("JOB COMPLETE: No pending targets and no active workers.", "bold green")
            log("Turning Global Switch OFF.", "green")
            db.set_global_automation(False)
            continue

        # 5. Inventory Check (Low Inventory Pause)
        if pending_targets < SESSION_CONFIG['min_batch_start'] and len(active_processes) == 0:
            log(f"Inventory low ({pending_targets}). Waiting for targets...", "yellow")
            smart_sleep_and_listen(30)
            continue

        # 6. API Sync
        try:
            live_api_devices = get_all_available_devices()
            db.sync_devices_with_api(live_api_devices)
            device_map = {d['id']: d for d in live_api_devices}
        except Exception as e:
            log(f"API Sync Warning: {e}", "yellow")
            smart_sleep_and_listen(30)
            continue

        # 7. ALLOCATION PASS
        runnable = db.get_runnable_accounts()
        launched_this_cycle = 0

        for acc in runnable:
            process_command_queue() # Check for stops mid-loop

            if acc.device_id in active_processes: continue 
            
            # HARD COOLDOWN CHECK (Priority 1 - survives reboots)
            cooldown_remaining = db.get_account_cooldown_remaining(acc.device_id)
            if cooldown_remaining is not None:
                log(f"Status Check [{acc.profile_name}]:", "bold cyan")
                log(f"  -> HARD COOLDOWN: {cooldown_remaining} minutes remaining. Skipping.", "yellow")
                continue
            
            stats = db.get_account_heat_stats(acc.device_id)

            log(f"Status Check [{acc.profile_name}]:", "bold cyan")
            log(f"  -> Session (2h Rolling): {stats['recent_2h']}/{SESSION_CONFIG['session_limit_2h']}", "white")
            log(f"  -> Daily (24h Rolling): {stats['rolling_24h']}/{acc.daily_limit}", "white")

            if stats['rolling_24h'] >= acc.daily_limit:
                log(f"  -> {acc.profile_name} hit Rolling 24h limit. Waiting for window to slide...", "yellow")
                continue

            space_24h = acc.daily_limit - stats['rolling_24h']
            space_2h = SESSION_CONFIG['session_limit_2h'] - stats['recent_2h']
            
            # Take the smallest of: batch cap, 2h remaining, 24h remaining, available targets
            batch_size = min(SESSION_CONFIG['batch_size'], space_2h, space_24h, pending_targets)

            if batch_size < SESSION_CONFIG['min_batch_start']:
                log(f"  -> SKIPPING: Remaining capacity ({batch_size}) is below min batch start ({SESSION_CONFIG['min_batch_start']}).", "dim")
                continue

            full_device_data = device_map.get(acc.device_id)
            if not full_device_data: continue

            targets = db.reserve_targets(acc.id, batch_size)
            if targets:
                log(f"SUCCESS: Launching {acc.profile_name} to process {len(targets)} targets.", "bold green")
                pending_targets -= len(targets) # Local decrement
                
                # NOTE: Cooldown is set by the WORKER when it completes successfully,
                # not here at launch. This ensures true 2-hour rest after actual work.

                a_port = 4723 + (len(active_processes) * 2)
                s_port = 8200 + len(active_processes)
                
                payload = {
                    'targets': targets, 
                    'config': SESSION_CONFIG, 
                    'static_device_id': acc.device_id
                }

                p = multiprocessing.Process(
                    target=run_automation_for_device,
                    args=(full_device_data, 'follow', a_port, s_port, payload)
                )
                p.start()
                active_processes[acc.device_id] = p
                launched_this_cycle += 1
                
                log(f"Staggering 5s...", "dim")
                smart_sleep_and_listen(5)

        # 8. STATUS REPORTING (Source of Truth for UI)
        # We loop through ALL active accounts in DB to set their display status
        # This runs every cycle so the DB is always fresh
        try:
            from database import Account, update_account_runtime_status
            all_accounts = Account.select().where(Account.status == 'active')
            
            for acc in all_accounts:
                new_status = "UNKNOWN"
                
                if not acc.is_enabled:
                    new_status = "DISABLED"
                elif acc.device_id in active_processes:
                    new_status = "RUNNING"
                else:
                    # It's enabled but not running. Why?
                    cooldown_remaining = db.get_account_cooldown_remaining(acc.device_id)
                    stats = db.get_account_heat_stats(acc.device_id)
                    
                    if cooldown_remaining is not None:
                        new_status = "COOLDOWN"
                    elif stats['rolling_24h'] >= acc.daily_limit:
                        new_status = "DAILY_LIMIT_HIT"
                    elif pending_targets < SESSION_CONFIG['min_batch_start']:
                        new_status = "NO_TARGETS"
                    else:
                        new_status = "IDLE" # Ready, just waiting for next cycle
                
                # Only write to DB if changed to save IO
                if acc.runtime_status != new_status:
                    update_account_runtime_status(acc.device_id, new_status)
                    
        except Exception as e:
            log(f"Status Update Error: {e}", "red")

        # 9. Adaptive Sleep
        if launched_this_cycle > 0:
            log(f"Cycle active. Pausing 15s...", "cyan")
            smart_sleep_and_listen(15)
        else:
            log("Manager Idle. Waiting 20...", "dim")
            smart_sleep_and_listen(20)
def main():
    try:
        rprint("[bold blue]Starting Farm Manager (Remote Control Ready)...[/bold blue]")
        db.initialize_db()
        perform_startup_cloud_audit()
        manager_loop()
    except KeyboardInterrupt:
        rprint("\n[bold red]Manual Shutdown Triggered.[/bold red]")
    finally:
        rprint("[bold yellow]CLEANUP INITIATED[/bold yellow]")
        
        # 1. Kill Processes
        for dev_id, proc in active_processes.items():
            if proc.is_alive():
                rprint(f"Terminating PID {proc.pid}...")
                proc.terminate()
        
        # 2. Release Leads
        from database import Target, set_global_automation
        count = Target.update(status='pending', reserved_by=None).where(Target.status == 'reserved').execute()
        rprint(f"Released {count} leads back to pending.")
        set_global_automation(False)
        rprint(f"Stopped Global Automation!")
        # 3. Stop Billing
        active_ids = list(active_processes.keys())
        if active_ids:
            rprint(f"[bold red]KILLING {len(active_ids)} CLOUD PHONES...[/bold red]")
            try: stop_phone(active_ids)
            except: pass
        
        # 4. RESET RUNTIME STATUS (The Fix)
        # Mark everything as DISABLED or IDLE so the UI doesn't show "Running" forever
        from database import Account
        Account.update(runtime_status="STOPPED").where(Account.status == 'active').execute()
        rprint("Account statuses reset to STOPPED.")

        rprint("[bold green]System offline.[/bold green]")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
