import uuid
import time
import hashlib
import requests
import json
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv(override=True)

app_id: str =  os.getenv("geelark_app_id")
api_key: str = os.getenv("geelark_api_key")

def generate_api_headers(app_id: str, api_key: str) -> dict:
    """
    Generates the required headers for the API request.

    Args:
        app_id: Your team's AppId.
        api_key: Your team's ApiKey.

    Returns:
        A dictionary containing the request headers.
    """
    trace_id = str(uuid.uuid4())
    ts = str(int(time.time() * 1000))
    nonce = trace_id[:6]

    # Concatenate the string for signature
    sign_str = app_id + trace_id + ts + nonce + api_key

    # Generate SHA256 hexadecimal uppercase digest
    sha256_hash = hashlib.sha256(sign_str.encode('utf-8')).hexdigest().upper()

    headers = {
        "Content-Type": "application/json",
        "appId": app_id,
        "traceId": trace_id,
        "ts": ts,
        "nonce": nonce,
        "sign": sha256_hash
    }
    return headers

def request_with_retry(
    method,
    url,
    headers=generate_api_headers(app_id,api_key),
    payload=None,
    retries=3,
    backoff=3) -> requests.Response | None:
    """
    Make an HTTP request with automatic retries on connection errors.

    Args:
        method (str): HTTP method ("GET", "POST", etc.)
        url (str): The API endpoint.
        headers (dict): HTTP headers.
        payload (dict or str): Request payload.
        retries (int): Number of retries on failure.
        backoff (int): Delay (seconds) between retries.

    Returns:
        requests.Response: Response object on success.
        None: If all retries failed.
    """
    for attempt in range(1, retries + 1):
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, data=payload, timeout=10)
            elif method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle Rate Limiting (429)
            if response.status_code == 429:
                print(f"[Attempt {attempt}/{retries}] Rate limit hit (429).")
                if attempt < retries:
                    # Longer backoff for rate limits
                    wait_time = backoff * 10 
                    print(f"Backing off for {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException) as e:
            print(f"[Attempt {attempt}/{retries}] Request failed: {e}")
            if attempt < retries:
                print(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                print("All retries failed.")
    return None

def get_all_cloud_phones(
    page: int = None,
    page_size: int = 100,
    ids: list[str] = None,
    serial_name: str = None,
    remark: str = None,
    group_name: str = None,
    tags: list[str] = None
) -> dict:


    api_url = "https://openapi.geelark.com/open/v1/phone/list"
    
    headers = generate_api_headers(app_id, api_key)
    
    payload = {}
    if page is not None:
        payload["page"] = page
    if page_size is not None:
        payload["pageSize"] = page_size
    if ids is not None:
        payload["ids"] = ids
    if serial_name is not None:
        payload["serialName"] = serial_name
    if remark is not None: 
        payload["remark"] = remark
    if group_name is not None: 
        payload["groupName"] = group_name
    if tags is not None: 
        payload["tags"] = tags

    response = request_with_retry(
        method="POST",
        url=api_url,
        headers=headers,
        payload=json.dumps(payload),
        retries=3,
        backoff=3,  # wait 5s between retries
    )

    if response:
        try:
            response_data = response.json()
            if response_data.get("code") == 0:
                return response_data["data"]["items"]
            else:
                print(f"API Error in get_all_cloud_phones: {response_data.get('msg')}")
                return None # Return None on API error
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return None
    else:
        print("Could not retrieve cloud phones after retries.")
        return None

def start_phone(ids: list[str]) -> dict | None:
    """
    Start the specified cloud phones and open their URLs in the browser.

    Args:
        ids (list[str]): List of cloud phone IDs to start

    Returns:
        dict | None: API response dictionary on success, None on failure.
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/start"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    response = request_with_retry(
        method="POST",
        url=api_url,
        payload=json.dumps(payload),
        retries=3,    # Retry up to 3 times
        backoff=5     # Wait 5 seconds between retries
    )

    if response:
        try:
            response_data = response.json()
            if response_data.get("code") == 0:
                # Open each phone's URL in the browser
                success_details = response_data.get("data", {}).get("successDetails", [])
                for phone in success_details:
                    url = phone.get("url")
                    id = phone.get("id")
                    if url:
                        print(f"Opening phone {phone.get('id')} in browser...")
                        with open(f"gee-browse-{id}.txt", "w") as file:
                            file.write(url)
                        webbrowser.open(url)
                        time.sleep(1)  # Small delay between opening multiple URLs

                return success_details
            else:
                print(f"API Error: {response_data.get('msg')}")
            return response_data
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return None
    else:
        print("Failed to start phones after retries.")
        return None

def stop_phone(ids: list[str]) -> dict | None:
    """
    Stop the specified cloud phones.
    Args:
        ids (list[str]): List of cloud phone IDs to stop
    Returns:
        dict | None: API response dictionary on success, None on failure.
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/stop"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    response = request_with_retry(
        method="POST",
        url=api_url,
        headers=headers,
        payload=json.dumps(payload),
        retries=3,
        backoff=5,
    )

    if response:
        try:
            response_data = response.json()
            return response_data
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return None
    else:
        print("Failed to stop phones after retries.")
        return None

def get_adb_information(ids: list[str]) -> list[dict]:
    """
    Get ADB connection information for specified cloud phones.

    Args:
        ids (list[str]): List of cloud phone IDs to get ADB information for

    Returns:
        list[dict]: List of ADB connection details for each phone.
    """
    api_url = "https://openapi.geelark.com/open/v1/adb/getData"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    response = request_with_retry(
        method="POST",
        url=api_url,
        headers=headers,
        payload=json.dumps(payload),
        retries=5,
        backoff=15,
    )

    if response:
        try:
            response_data = response.json()
            if response_data.get("code") == 0:
                return response_data.get("data", {}).get("items", [])
            else:
                print(f"API Error: {response_data.get('msg')}")
                return []
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return []
    else:
        print("Failed to get ADB information after retries.")
        return []

def get_available_phones(adb_enabled=True) -> list[dict]:
    """
    Get a list of available phones based on their remark field.
    Phones are considered available if their remark doesn't contain 'inactive'.

    Returns:
        list[dict]: List of available phones with their details.
    """
    # Get all phones
    phones = get_all_cloud_phones()
    if phones is None:
        print("No phones retrieved due to API error.")
        return None # Propagate None to indicate error

    # Filter and format available phones
    available_phones = []
    for phone in phones:
        remark = phone.get("remark", "").lower()
        if "inactive" not in remark:
            equipment_info = phone.get("equipmentInfo", {})
            phone_info = {
                "id": phone.get("id"),
                "name": phone.get("serialName", "Unknown"),
                "status": "active",
                "brand": equipment_info.get("deviceBrand", "Unknown"),
                "model": equipment_info.get("deviceModel", "Unknown")
            }
            available_phones.append(phone_info)

    # Get ADB info for available phones
    phone_ids = [phone["id"] for phone in available_phones]
    adb_info = get_adb_information(phone_ids)

    if adb_enabled:
        # Filter out phones where ADB is not enabled (code 49001)
        return [
            phone for phone in available_phones
            if not any(adb["id"] == phone["id"] and adb["code"] == 49001 for adb in adb_info)
        ]
    return available_phones

def get_phone_status(ids: list[str]) -> dict:
    """
    Query the status of cloud phones by their IDs.

    Args:
        ids (list[str]): List of cloud phone IDs to query status for (max 100 elements)

    Returns:
        dict: Response containing status details for each phone, or empty dict on failure.

    Response format:
    {
        "totalAmount": int,
        "successAmount": int,
        "failAmount": int,
        "successDetails": [
            {
                "id": str,
                "serialName": str,
                "status": int  # 0=Started, 1=Starting, 2=Shut down, 3=Expired
            }
        ],
        "failDetails": [
            {
                "code": int,
                "id": str,
                "msg": str
            }
        ]
    }
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/status"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    response = request_with_retry(
        method="POST",
        url=api_url,
        headers=headers,
        payload=json.dumps(payload),
        retries=3,
        backoff=5,
    )

    if response:
        try:
            response_data = response.json()
            if response_data.get("code") == 0:
                return response_data.get("data", {})
            else:
                print(f"API Error: {response_data.get('msg')}")
                return {}
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return {}
    else:
        print("Failed to get phone status after retries.")
        return {}



def start_app(ids: list[str]) -> dict | None:
    """
    Start the specified cloud phones and open their URLs in the browser.

    Args:
        ids (list[str]): List of cloud phone IDs to start

    Returns:
        dict | None: API response dictionary on success, None on failure.
    """
    api_url = "https://openapi.geelark.com/open/v1/phone/start"
    headers = generate_api_headers(app_id, api_key)
    payload = {"ids": ids}

    response = request_with_retry(
        method="POST",
        url=api_url,
        headers=headers,
        payload=json.dumps(payload),
        retries=3,    # Retry up to 3 times
        backoff=5     # Wait 5 seconds between retries
    )

    if response:
        try:
            response_data = response.json()
            if response_data.get("code") == 0:
                # Open each phone's URL in the browser
                success_details = response_data.get("data", {}).get("successDetails", [])
                return success_details
                for phone in success_details:
                    url = phone.get("url")
                    if url:
                        print(f"Opening phone {phone.get('id')} in browser...")
                        webbrowser.open(url)
                        time.sleep(1)  # Small delay between opening multiple URLs
            else:
                print(f"API Error: {response_data.get('msg')}")
            return response_data
        except Exception as e:
            print(f"Failed to parse response JSON: {e}")
            return None
    else:
        print("Failed to start phones after retries.")
        return None

if __name__ == '__main__':
    print("Getting available phones (excluding those with ADB not enabled)...")
    available_phones = get_available_phones()
    print("\nAvailable phones:")
    print(json.dumps(available_phones, indent=4))


