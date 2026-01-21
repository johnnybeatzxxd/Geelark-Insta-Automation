from geelark_api import get_all_cloud_phones, start_phone, stop_phone, request_with_retry
from connection import connect_to_phone
from services import start_appium_service_instance, manage_adb_server, start_automation_specific, start_automation_all
import webbrowser
import time

def main():
    print("Hello from geelark-insta-automation!")
    start_automation_all()


if __name__ == "__main__":
    main()
