import urllib.request
import time
import sys

def check_app_status(url="http://localhost:8501", max_retries=10):
    print(f"Checking {url}...")
    for i in range(max_retries):
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    print("App is running and responding with 200 OK.")
                    return True
        except Exception as e:
            # Only print if it's not the encoding error (which happens on success print too if not careful)
            # But here we are in except block
            pass 
            
        print(f"Attempt {i+1}: Retrying...")
        time.sleep(2)
            
    print("Failed to connect to app after retries.")
    return False

if __name__ == "__main__":

    success = check_app_status()
    sys.exit(0 if success else 1)
