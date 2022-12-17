"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

from scrapli.driver.core import IOSXEDriver
from scrapli.exceptions import ScrapliAuthenticationFailed, ScrapliPrivilegeError
from scrapli.settings import Settings
from rich import print
from rich.progress import Progress
from rich.prompt import Prompt, Confirm
from rich.table import Table
from ipaddress import ip_address

###
# Settings
#####

# Set the below value to True to remove the default Cisco call-home config
REMOVE_DEFAULT_PROFILE = True
DEFAULT_PROFILE_NAME = "CiscoTAC-1"

# New Smart licensing profile name to be configured on device
PROFILE_NAME = ""

# Smart licensing server URL:
SSM_URL = ""

# License registration token:
TOKEN = ""

# Name of CSV file containing device IP addresses
DEVICE_LIST = ""

###
# Config sets
#####

# Commands to remove default profile:
REMOVE_SSM_CONFIG = ["call-home", f"no profile {DEFAULT_PROFILE_NAME}"]

# List of configuration commands to add new call-home profile
SSM_CONFIG = [
    "call-home",
    "no http secure server-identity-check",
    f"profile {PROFILE_NAME}",
    "reporting smart-licensing-data",
    "destination transport-method http",
    f"destination address http {SSM_URL}",
    "destination preferred-msg-format xml",
    "active",
    "exit",
]

# Command to request device to register via smart licensing
LICENSE_REGISTER_COMMAND = f"license smart register idtoken {TOKEN}"

# Disable scrapli's default warnings
Settings.SUPPRESS_USER_WARNINGS = True


def loadDeviceList():
    """
    Collect device info from CSV
    """
    print("[bold]Loading device list...")
    valid_ips = []
    invalid_ips = []
    with open(DEVICE_LIST, "r") as file:
        for line in file:
            line = line.strip()
            # Skip blank lines:
            if line == "":
                continue
            try:
                # Validate IP address
                ip_address(line)
                valid_ips.append(line)
            except ValueError:
                # Collect invalid addresses
                invalid_ips.append(line)
    print(
        f"Devices loaded: {len(valid_ips)} valid IP addresses & {len(invalid_ips)} invalid."
    )
    return valid_ips, invalid_ips


def connectSSH(device, user, password, enable_password):
    """
    Open SSH connection to target device
    """
    # Default device connection parameters
    device = {
        "host": device,
        "auth_username": user,
        "auth_password": password,
        "auth_strict_key": False,
    }
    # Add enable password, if one was provided
    if enable_password:
        device["auth_secondary"] = enable_password
    # Avoid issue with cipher mismatch on certain devices
    device["transport_options"] = {
        "open_cmd": [
            "-o",
            "KexAlgorithms=+diffie-hellman-group-exchange-sha1",
            "-o",
            "Ciphers=+aes256-cbc",
        ]
    }
    # Establish connection
    conn = IOSXEDriver(**device)
    try:
        conn.open()
    except ScrapliAuthenticationFailed as e:
        return None, str(e)
    except ScrapliPrivilegeError as e:
        return None, str(e)
    return conn, None


def updateConfiguration(iplist, user, password, enable_password):
    """
    Push new configuration to devices
    """
    status = {}
    status["errors"] = {}
    status["success"] = []

    with Progress() as progress:
        task = progress.add_task("Send Config", total=len(iplist))
        for ip in iplist:
            progress.console.print(f"\n[bold]> Working on {ip}")

            # Step 1: Connect to target device
            progress.console.print("Connecting to device...")
            c, err = connectSSH(ip, user, password, enable_password)
            # If failed to connect, save error & skip to next device
            if err:
                progress.console.print("[red]Failed to connect.")
                status["errors"][ip] = err
                progress.advance(task)
                continue
            else:
                print("[green]Connected")

            # Step 2: Remove default call-home profile, if requested
            if REMOVE_DEFAULT_PROFILE:
                progress.console.print(
                    f"Removing default call-home profile {DEFAULT_PROFILE_NAME}"
                )
                result = c.send_configs(REMOVE_SSM_CONFIG)
                if result.failed:
                    progress.console.print("[red]Config removal failed")
                    status["errors"][ip] = result.result
                    c.close()
                    progress.advance(task)
                    continue
                else:
                    print("[green]Default profile removed")

            # Step 3: Apply new call-home config
            progress.console.print("Sending new config...")
            result = c.send_configs(SSM_CONFIG)
            # If config failed, save error msg & skip rest of task
            if result.failed:
                progress.console.print("[red]Config failed")
                status["errors"][ip] = result.result
                c.close()
                progress.advance(task)
                continue
            else:
                print("[green]Configuration applied")

            # Step 4: Ask device to perform license registration
            progress.console.print(f"Requesting license registration...")
            result = c.send_command(LICENSE_REGISTER_COMMAND)
            if result.failed:
                progress.console.print("[red]Failed to register license")
                status["errors"][ip] = result.result
                c.close()
                progress.advance(task)
                continue
            else:
                print("[green]Request succeeded")

            progress.console.print("Done!")
            status["success"].append(ip)
            c.close()
            progress.advance(task)
    return status


def printResults(status, bad_ips):
    """
    Print script results & errors
    """
    # Print quick status of how many succeeded/failed
    print("\n\n[green]Script Completed!")
    success = status["success"]
    errors = status["errors"]
    print(f"{len(success)} devices were configured successfully.")
    if len(errors) > 0:
        print(f"[red]{len(errors)} errors occured.")

    # Optionally print detailed table with error messages
    if Confirm.ask("\nPrint details?"):
        table = Table(title="Configuration Change Report")
        table.add_column("IP Address")
        table.add_column("Status")
        table.add_column("Error")
        for device in success:
            table.add_row(device, "[green]Successful", "")
        for error in errors:
            table.add_row(error, "[red]Failed", errors[error])
        for ip in bad_ips:
            table.add_row(ip, "[red]Failed", "Invalid IP address")
        print("")
        print(table)


def run():
    # Load device file
    iplist, bad_ips = loadDeviceList()

    # Collect device credentials
    print("\n[bold]Please provide device credentials:")
    user = Prompt.ask("Username")
    password = Prompt.ask("Password", password=True)
    if Confirm.ask("Provide enable password?"):
        enable_pw = Prompt.ask("Enable Password", password=True)
    else:
        enable_pw = None

    # Send desired configuration changes
    status = updateConfiguration(iplist, user, password, enable_pw)

    # Print script results
    printResults(status, bad_ips)


if __name__ == "__main__":
    run()
