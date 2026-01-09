import subprocess
import re
from typing import List, Dict

def get_local_devices() -> List[Dict]:
    """
    Get a list of locally connected ADB devices.
    
    Returns:
        List[Dict]: List of local devices with their details
        Example format:
        [
            {
                "id": "device_serial",
                "name": "device_name",
                "status": "device",
                "brand": "brand_name",
                "model": "model_name",
                "type": "local"
            }
        ]
    """
    try:
        # Run adb devices command
        result = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, check=True)
        
        # Parse the output
        devices = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip the first line (header)
        
        for line in lines:
            if not line.strip():
                continue
                
            parts = line.split()
            if len(parts) < 2:
                continue
                
            device_id = parts[0]
            status = parts[1]
            
            if status != "device":
                continue
                
            # Get device model and brand
            try:
                model_cmd = ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"]
                brand_cmd = ["adb", "-s", device_id, "shell", "getprop", "ro.product.brand"]
                
                model = subprocess.run(model_cmd, capture_output=True, text=True, check=True).stdout.strip()
                brand = subprocess.run(brand_cmd, capture_output=True, text=True, check=True).stdout.strip()
                
                device_info = {
                    "id": device_id,
                    "name": f"{brand} {model}",
                    "status": "active",
                    "brand": brand,
                    "model": model,
                    "type": "local"
                }
                devices.append(device_info)
            except subprocess.CalledProcessError:
                # If we can't get device info, still add the device with basic info
                device_info = {
                    "id": device_id,
                    "name": device_id,
                    "status": "active",
                    "brand": "Unknown",
                    "model": "Unknown",
                    "type": "local"
                }
                devices.append(device_info)
                
        return devices
        
    except subprocess.CalledProcessError as e:
        print(f"Error getting local devices: {e.stderr.decode()}")
        return []
    except Exception as e:
        print(f"Unexpected error getting local devices: {str(e)}")
        return []
