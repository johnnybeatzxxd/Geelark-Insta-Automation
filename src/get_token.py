import requests
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from dotenv import load_dotenv

load_dotenv()
console = Console()

# --- CONFIGURATION ---
# Ensure this matches your running backend URL
API_URL = "http://localhost:8000" 
ADMIN_SECRET = os.getenv("ADMIN_PASSWORD")

def generate_client_token():
    console.print("[bold blue]--- Geelark Token Generator ---[/bold blue]")

    # 1. Get Client Name
    client_name = Prompt.ask("Enter the Client Name (e.g. 'Client_A')")
    
    if not client_name:
        console.print("[red]Client name is required.[/red]")
        return

    payload = {
        "client_name": client_name,
        "admin_secret": ADMIN_SECRET
    }

    try:
        # 2. Send Request to Backend
        with console.status("[bold green]Requesting token from API...[/bold green]"):
            response = requests.post(f"{API_URL}/generate-token", json=payload)

        # 3. Handle Response
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            expires = data.get("expires_in_days")
            
            console.print(Panel(
                f"[bold green]SUCCESS![/bold green]\n\n"
                f"[bold yellow]Client:[/bold yellow] {client_name}\n"
                f"[bold yellow]Expires:[/bold yellow] {expires} days\n\n"
                f"[bold cyan]Token:[/bold cyan]\n{token}",
                title="Generated JWT",
                expand=False
            ))
            
            # Optional: Save to file
            with open("latest_token.txt", "w") as f:
                f.write(token)
            console.print("\n[dim]Token saved to 'latest_token.txt' for easy copying.[/dim]")
            
        elif response.status_code == 403:
            console.print(f"[bold red]Error: Invalid Admin Secret.[/bold red]")
            console.print(f"Check the 'MASTER_PASSWORD' in your main.py vs this script.")
            
        else:
            console.print(f"[bold red]Error {response.status_code}:[/bold red] {response.text}")

    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]Connection Refused![/bold red]")
        console.print(f"Is the backend running at {API_URL}?")

if __name__ == "__main__":
    generate_client_token()
