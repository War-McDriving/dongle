import subprocess
import platform
import csv
import re
import time
from datetime import datetime

# Get the name of the operating system.
os_name = platform.system()

# Open the CSV file in append mode.
with open('wifi_networks.csv', mode='a', newline='') as file:
    writer = csv.writer(file)

    # Write the header row only if the CSV is empty
    if file.tell() == 0:
        writer.writerow(['Timestamp', 'SSID', 'BSSID', 'Signal Strength', 'Authentication', 'Encryption', 'Bandwidth'])

    print("Script is running. Receiving data...")  # Initial message indicating the script is running.
    
    try:
        while True:
            # Get the current timestamp.
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Check if the OS is Windows.
            if os_name == "Windows":
                # Command to list Wi-Fi networks on Windows using netsh.
                list_networks_command = 'netsh wlan show networks mode=bssid'
                # Execute the command and capture the result.
                output = subprocess.check_output(list_networks_command, shell=True, text=True)

                # Split the output into individual SSID blocks.
                ssid_blocks = output.split('\n\n')
                for block in ssid_blocks:
                    ssid = bssid = signal_strength = authentication = encryption = bandwidth = 'N/A'
                    
                    # Extract SSID (sometimes blank SSID can appear)
                    ssid_match = re.search(r"SSID\s*\d+\s*:\s*(.+)", block)
                    if ssid_match:
                        ssid = ssid_match.group(1).strip()

                    # Extract Authentication and Encryption values for the SSID block.
                    auth_match = re.search(r"Authentication\s*:\s*(\S+)", block)
                    enc_match = re.search(r"Encryption\s*:\s*(\S+)", block)
                    if auth_match:
                        authentication = auth_match.group(1).strip()
                    if enc_match:
                        encryption = enc_match.group(1).strip()

                    # Extract Band (Bandwidth) for the SSID block.
                    band_match = re.search(r"Band\s*:\s*(\S+)", block)
                    if band_match:
                        bandwidth = band_match.group(1).strip()

                    # Find each BSSID entry.
                    bssid_entries = re.findall(r"BSSID\s*\d+\s*:\s*(\S+)", block)
                    signal_entries = re.findall(r"Signal\s*:\s*(\d+)%", block)
                    if len(bssid_entries) == len(signal_entries):
                        for bssid, signal in zip(bssid_entries, signal_entries):
                            # Write the extracted info for each BSSID to the CSV.
                            writer.writerow([timestamp, ssid, bssid, f"{signal}%", authentication, encryption, bandwidth])

            # Handle Linux (optional).
            elif os_name == "Linux":
                # Command to list Wi-Fi networks on Linux using nmcli.
                list_networks_command = "nmcli device wifi list"
                # Execute the command and capture the output.
                output = subprocess.check_output(list_networks_command, shell=True, text=True)

                # Parse the output for network details.
                lines = output.split('\n')
                for line in lines[1:]:  # Skip header line
                    parts = line.split()
                    if len(parts) >= 6:
                        ssid = parts[0]
                        bssid = parts[1]
                        signal_strength = parts[2]
                        authentication = 'N/A'  # nmcli doesn't show authentication directly, this needs to be inferred
                        encryption = parts[-3]
                        bandwidth = parts[-1]
                        
                        # Write the network info to CSV.
                        writer.writerow([timestamp, ssid, bssid, signal_strength, authentication, encryption, bandwidth])

            # Handle unsupported operating systems.
            else:
                print("Unsupported OS")

            # Print message indicating the script is actively running and receiving data.
            print(f"Data received at {timestamp}, refreshing every 10 seconds...")
            print("Close program: Ctrl + c")

            # Sleep for 10 seconds before refreshing.
            time.sleep(10)
    
    except KeyboardInterrupt:
        # Graceful exit message.
        print("\nProgram closed successfully.")
