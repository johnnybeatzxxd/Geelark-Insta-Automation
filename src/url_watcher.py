import os
import glob
import time
import webbrowser

def monitor_and_open():
    print("Monitoring for 'gee-browse*.txt' files... (Press Ctrl+C to stop)")
    
    file_pattern = "gee-browse*.txt"

    while True:
        try:
            found_files = glob.glob(file_pattern)

            for file_path in found_files:
                try:
                    with open(file_path, 'r') as f:
                        url = f.read().strip()

                    if url:
                        print(f"Found {file_path}. Opening: {url}")
                        
                        webbrowser.open(url)
                    else:
                        print(f"Found {file_path}, but it was empty.")

                    os.remove(file_path)
                    print(f"Deleted {file_path}")

                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping script...")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(1)

if __name__ == "__main__":
    monitor_and_open()
