from geelark_api import get_all_cloud_phones, start_phone, stop_phone, request_with_retry
from connection import connect_to_phone
from services import start_appium_service_instance, manage_adb_server, start_automation_specific, start_automation_all
import webbrowser
import time

def main():
    print("Hello from geelark-insta-automation!")

    start_automation_all()
    # connection_info = connect_to_phone("")

    appium_port = 4723
    system_port = 8200
    server_url = f"http://127.0.0.1:{appium_port}/wd/hub"

    # appium_service = start_appium_service_instance('127.0.0.1', appium_port, system_port)
    # print(appium_service)


if __name__ == "__main__":
    main()
