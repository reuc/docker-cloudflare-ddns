import os, time, requests
from datetime import datetime as dt
from pytz import timezone as tz

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.error import HTTPError
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import HTTPError
    from urllib2 import URLError

import json


def log_message(message, level="INFO"):
    """Log message to docker console with timestamp and level"""
    timestamp = dt.now(tz('UTC')).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(f"[{timestamp}] [{level}] {message}")


def get_cloudflare_token():
    """Get the CloudFlare API token from environment variables"""
    token = os.environ.get('CLOUDFLARE_TOKEN')
    if not token:
        log_message("CLOUDFLARE_TOKEN environment variable is not set", "ERROR")
        return None
    return token


def get_public_ip():
    """Get the public IP address"""
    try:
        response = requests.get('https://api.ipify.org', timeout=10)
        if response.status_code == 200:
            return response.text.strip()
        raise Exception(f"Failed to get IP: Status code {response.status_code}")
    except Exception as e:
        log_message(f"Error getting public IP: {str(e)}", "ERROR")
        return None

#

def get_cloudflare_record():
    """Get the current DNS record from CloudFlare"""
    token = get_cloudflare_token()
    if not token:
        return None

    zone_id = os.environ.get('CLOUDFLARE_ZONEID')
    record_name = os.environ.get('CLOUDFLARE_NAME')
    zone_name = os.environ.get('CLOUDFLARE_ZONE')
    record_type = os.environ.get('CLOUDFLARE_RECORDTYPE')

    full_domain = f"{record_name}.{zone_name}" if record_name != '@' else zone_name

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"type": record_type, "name": full_domain}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            error_detail = response.json() if response.text else "No detail provided"
            log_message(f"CloudFlare API error: {response.status_code}, Details: {error_detail}", "ERROR")
        response.raise_for_status()
        data = response.json()

        if data["success"] and data["result"]:
            return data["result"][0]
        return None
    except Exception as e:
        log_message(f"Error getting DNS record: {str(e)}", "ERROR")
        return None


def update_cloudflare_record(record_id, ip_address):
    """Update CloudFlare DNS record with new IP"""
    token = get_cloudflare_token()
    if not token:
        return False

    zone_id = os.environ.get('CLOUDFLARE_ZONEID')
    record_name = os.environ.get('CLOUDFLARE_NAME')
    zone_name = os.environ.get('CLOUDFLARE_ZONE')
    record_type = os.environ.get('CLOUDFLARE_RECORDTYPE')
    ttl = int(os.environ.get('CLOUDFLARE_RECORDTTL'))

    full_domain = f"{record_name}.{zone_name}" if record_name != '@' else zone_name

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "type": record_type,
        "name": full_domain,
        "content": ip_address,
        "ttl": ttl,
        "proxied": False
    }

    try:
        response = requests.put(url, headers=headers, json=data)
        if response.status_code != 200:
            error_detail = response.json() if response.text else "No detail provided"
            log_message(f"CloudFlare API error: {response.status_code}, Details: {error_detail}", "ERROR")
        response.raise_for_status()
        return response.json()["success"]
    except Exception as e:
        log_message(f"Error updating DNS record: {str(e)}", "ERROR")
        return False


def create_cloudflare_record(ip_address):
    """Create a new CloudFlare DNS record"""
    token = get_cloudflare_token()
    if not token:
        return False

    zone_id = os.environ.get('CLOUDFLARE_ZONEID')
    record_name = os.environ.get('CLOUDFLARE_NAME')
    zone_name = os.environ.get('CLOUDFLARE_ZONE')
    record_type = os.environ.get('CLOUDFLARE_RECORDTYPE')
    ttl = int(os.environ.get('CLOUDFLARE_RECORDTTL'))

    full_domain = f"{record_name}.{zone_name}" if record_name != '@' else zone_name

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "type": record_type,
        "name": full_domain,
        "content": ip_address,
        "ttl": ttl,
        "proxied": False
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            error_detail = response.json() if response.text else "No detail provided"
            log_message(f"CloudFlare API error: {response.status_code}, Details: {error_detail}", "ERROR")
        response.raise_for_status()
        return response.json()["success"]
    except Exception as e:
        log_message(f"Error creating DNS record: {str(e)}", "ERROR")
        return False


def main():
    log_message("Starting CloudFlare DDNS updater")

    # Get configuration from environment
    delay = int(os.environ.get('CLOUDFLARE_DELAY'))
    interval = int(os.environ.get('CLOUDFLARE_INTERVAL'))
    max_tries = int(os.environ.get('CLOUDFLARE_TRIES'))
    static_ip = os.environ.get('CLOUDFLARE_IPV4')

    # Initial delay
    if delay > 0:
        log_message(f"Waiting for initial delay of {delay} seconds")
        time.sleep(delay)

    # Main loop
    while True:
        tries = 0
        success = False

        while tries < max_tries and not success:
            try:
                # Get current IP or use static if provided
                current_ip = static_ip if static_ip else get_public_ip()
                if not current_ip:
                    raise Exception("Failed to get IP address")

                log_message(f"Current IP address: {current_ip}")

                # Get existing record
                record = get_cloudflare_record()

                if record:
                    if record["content"] != current_ip:
                        log_message(f"IP changed: {record['content']} -> {current_ip}")
                        if update_cloudflare_record(record["id"], current_ip):
                            log_message("Successfully updated DNS record")
                            success = True
                        else:
                            raise Exception("Failed to update DNS record")
                    else:
                        log_message("IP unchanged, no update needed")
                        success = True
                else:
                    log_message("No DNS record found, creating new record")
                    if create_cloudflare_record(current_ip):
                        log_message("Successfully created DNS record")
                        success = True
                    else:
                        raise Exception("Failed to create DNS record")

            except Exception as e:
                tries += 1
                log_message(f"Attempt {tries}/{max_tries} failed: {str(e)}", "ERROR")
                if tries < max_tries:
                    time.sleep(10)

        log_message(f"Sleeping for {interval} seconds until next check")
        time.sleep(interval)


if __name__ == "__main__":
    main()