import subprocess
import gpsd
import csv
import time
import signal
import sys

# Global dictionary to track logged SSIDs and their GPS locations
logged_ssids = {}

# Function to connect to GPS and get location data
def get_gps_location():
    try:
        gpsd.connect()  # Connect to the gpsd daemon
        packet = gpsd.get_current()

        if packet.mode >= 2:  # Ensure we have at least a 2D fix
            latitude = packet.lat
            longitude = packet.lon
            altitude = packet.alt
            return latitude, longitude, altitude
        else:
            return None, None, None
    except Exception as e:
        print(f"Error fetching GPS data: {e}")
        return None, None, None

# Function to get wireless interfaces from airmon-ng
def get_wireless_interfaces():
    try:
        result = subprocess.run(['sudo', 'airmon-ng'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        interfaces = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith("PHY"):
                interfaces.append(parts[1])
        return interfaces
    except Exception as e:
        print(f"Error fetching wireless interfaces: {e}")
        return []

# Function to enable monitor mode
def enable_monitor_mode(interface):
    try:
        subprocess.run(['sudo', 'airmon-ng', 'start', interface], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error enabling monitor mode on {interface}: {e}")
        raise e

# Function to disable monitor mode
def disable_monitor_mode(interface):
    try:
        subprocess.run(['sudo', 'airmon-ng', 'stop', f"{interface}mon"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error disabling monitor mode on {interface}: {e}")

# Function to kill conflicting processes
def kill_conflicting_processes():
    try:
        subprocess.run(['sudo', 'airmon-ng', 'check', 'kill'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error killing conflicting processes: {e}")

# Function to capture Wi-Fi data with airodump-ng and save to CSV
def capture_wifi_data(interface):
    try:
        # Run airodump-ng and capture output for 10 seconds
        print(f"Running airodump-ng on {interface}mon...")
        process = subprocess.Popen(
            ['sudo', 'airodump-ng', '--write', '/tmp/airodump', '--output-format', 'csv', f'{interface}mon'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return process
    except Exception as e:
        print(f"Error capturing Wi-Fi data: {e}")
        return None

# Function to process the CSV and add GPS data
def process_wifi_data(csv_filename, latitude, longitude, altitude):
    try:
        # Read the generated CSV file and append to the final output CSV
        with open('/tmp/airodump-01.csv', 'r') as infile, open(csv_filename, 'a', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            for row in reader:
                if len(row) > 13 and row[0].strip():  # Ensure the row contains valid Wi-Fi data
                    ssid = row[13].strip()
                    mac = row[0].strip()
                    channel = row[3].strip()
                    signal = row[8].strip()

                    # Avoid duplicate entries or mismatched data
                    if ssid not in logged_ssids:
                        logged_ssids[ssid] = (latitude, longitude, altitude)
                        writer.writerow([ssid, mac, channel, signal, latitude, longitude, altitude])
                    else:
                        # Check for location inconsistency
                        if logged_ssids[ssid] != (latitude, longitude, altitude):
                            print(f"Warning: SSID {ssid} seen at different locations!")
    except Exception as e:
        print(f"Error processing Wi-Fi data: {e}")

# Signal handler to gracefully stop the script on CTRL+C
def signal_handler(sig, frame):
    print("Stopping Wi-Fi capture...")
    sys.exit(0)

# Main function to integrate GPS and airmon-ng
def main():
    # Register the signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)

    print("Fetching GPS location...")
    latitude, longitude, altitude = get_gps_location()
    if latitude is None:
        print("No GPS fix available. Proceeding with Wi-Fi scan only.")

    print("Scanning for wireless interfaces...")
    interfaces = get_wireless_interfaces()

    if not interfaces:
        print("No wireless interfaces found!")
        return

    print(f"Found interfaces: {interfaces}")
    kill_conflicting_processes()

    for iface in interfaces:
        try:
            enable_monitor_mode(iface)
            csv_filename = f'WiFi_scan_{iface}.csv'

            # Create or overwrite the CSV file and add header
            with open(csv_filename, 'w', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['SSID', 'MAC', 'Channel', 'Signal', 'Latitude', 'Longitude', 'Altitude'])

            # Continuous Wi-Fi capture and data processing loop
            while True:
                process = capture_wifi_data(iface)
                if process:
                    time.sleep(10)  # Wait for 10 seconds before processing the data again
                    process.terminate()  # Terminate the airodump-ng process
                    latitude, longitude, altitude = get_gps_location()
                    process_wifi_data(csv_filename, latitude, longitude, altitude)  # Process the data and save it to CSV
                else:
                    break

        except Exception as e:
            print(f"Error processing interface {iface}: {e}")
        finally:
            disable_monitor_mode(iface)

    print("Script completed.")

if __name__ == "__main__":
    main()