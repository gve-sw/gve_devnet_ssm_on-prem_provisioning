# Cisco SSM On-Prem Provisioning

This repo contains example code to demonstrate automated configuration provisioning for devices to use an on-prem Smart Software Manager (SSM).

This code will:

- Connect to a provided list of devices
- Remove default SSM call-home profiles
- Apply new SSM call-home profile
- Apply device license registration token

## Contacts

- Matt Schmitz (mattsc@cisco.com)

## Solution Components

- Cisco IOS-XE devices

## Installation/Configuration

### **1 - Clone repo**

```bash
git clone <repo_url>
```

### **2 - Install dependancies**

```bash
pip install -r requirements.txt
```

### **3 - Update script configuration**

In order to use this code, a few configuration items must be provided.

Within the `send_config.py` script, please update the values under **Settings**:

```python
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
```

Please note, the `DEVICE_LIST` value must point to a local file name, which contains a CSV list of device IP addresses separated by line.

For example, set `DEVICE_LIST = "device_list.csv"` which contains contents such as the following:

```
10.10.10.1
10.10.10.2
10.10.10.3
```

### **4 - Run script**

Run the script with the following command:

```bash
python3 send_config.py
```

### **Optional - Modify configuration command sets**

The default command sets that are included with this script apply to a Catalyst 9200 series switch, based on [this guide](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9200/software/release/16-9/configuration_guide/sys_mgmt/b_169_sys_mgmt_9200_cg/cisco_smart_licensing_client.html#task_lnl_w5p_qgb).

Depending on the device & firmware version, the required commands may differ. If needed, please edit the commands under the **Config Sets** section of the script:

```python
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
```

# Screenshots

**Example of script execution:**

![/IMAGES/example_script.png](/IMAGES/example_script.png)

### LICENSE

Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT

Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING

See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER

<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.
