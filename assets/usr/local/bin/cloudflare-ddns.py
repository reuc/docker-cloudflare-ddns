import os, time, requests
from datetime import datetime as dt
from pytz import timezone as tz

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.error import HTTPError
    # import urllib.parse
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import HTTPError
    from urllib2 import URLError

import json

# log message
def log(level, msg):
    now = dt.now(tz(os.getenv('TZ')))
    datetime = now.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3] + now.strftime('%z')
    print(datetime + '|dnsomatic|' + level + '|' + msg)
    return

email = os.getenv('CLOUDFLARE_EMAIL')
apikey = os.getenv('CLOUDFLARE_APIKEY')
delay = os.getenv('CLOUDFLARE_DELAY')
interval = os.getenv('CLOUDFLARE_INTERVAL')
tries = os.getenv('CLOUDFLARE_TRIES')
name = os.getenv('CLOUDFLARE_NAME')
zone = os.getenv('CLOUDFLARE_ZONE')
record_type = os.getenv('CLOUDFLARE_RECORDTYPE')
recordttl = os.getenv('CLOUDFLARE_RECORDTTL')
ipv4 = os.getenv('CLOUDFLARE_IPV4')
zoneid = os.getenv('CLOUDFLARE_ZONEID')

# delay startup
if delay > 0:
    log('INFO', 'Started with a ' + str(delay) + '-second delay')
    time.sleep(delay)

host = {}
domain = {'name': zone}
currentIp = ''
tried = 0
while True:
    headers = {'User-Agent': 'Docker_Updater/1.0'}
    try:
        update = False
        # get your IP address
        req = requests.get('http://myip.dnsomatic.com/')
        if req.status_code == 200:
            newIp = req.text
            if newIp != currentIp:
                if name != 'fqdn':
                    content_header = {'X-Auth-Email': email, 'X-Auth-Key': apikey, 'Content-type': 'application/json'}
                    base_url = 'https://api.cloudflare.com/client/v4/zones/'
                    update = True



                    if zoneid == "Domain Zone ID":
                        try:
                            print(
                                '* zone id for "{0}" is missing. attempting to '
                                'get it from cloudflare...'.format(domain['name']))
                            zone_id_req = Request(base_url, headers=content_header)
                            zone_id_resp = urlopen(zone_id_req)
                            for d in json.loads(zone_id_resp.read().decode('utf-8'))['result']:
                                if domain['name'] == d['name']:
                                    domain['id'] = d['id']
                                    print('* zone id for "{0}" is'
                                          ' {1}'.format(domain['name'], domain['id']))
                        except HTTPError as e:
                            print('* could not get zone id for: {0}'.format(domain['name']))
                            print('* possible causes: wrong domain and/or auth credentials')
                            continue

                    fqdn = name + '.' + zone

                    # get host id from CloudFlare if missing
                    if not host['id']:
                        print(
                            '* host id for "{0}" is missing. attempting'
                            ' to get it from cloudflare...'.format(fqdn))
                        rec_id_req = Request(
                            base_url + domain['id'] + '/dns_records/',
                            headers=content_header)
                        rec_id_resp = urlopen(rec_id_req)
                        parsed_host_ids = json.loads(rec_id_resp.read().decode('utf-8'))
                        for h in parsed_host_ids['result']:
                            if fqdn == h['name']:
                                host['id'] = h['id']
                                print('* host id for "{0}" is'
                                      ' {1}'.format(fqdn, host['id']))

                    if record_type == 'A':
                        if public_ipv4:
                            public_ip = public_ipv4
                            ip_version = 'ipv4'
                        else:
                            print('* cannot set A record because no IPv4 is available')
                            continue

                    if update:
                        try:
                            # make sure dns record type is specified (e.g A, AAAA)


                            data = json.dumps({
                                'id': host['id'],
                                'type': record_type,
                                'name': CLOUDFLARE_NAME,
                                'content': public_ip
                            })
                            url_path = '{0}{1}{2}{3}'.format(base_url,
                                                             domain['id'],
                                                             '/dns_records/',
                                                             host['id'])
                            update_request = Request(
                                url_path,
                                data=data.encode('utf-8'),
                                headers=content_header)
                            update_request.get_method = lambda: 'PUT'
                            update_res_obj = json.loads(
                                urlopen(update_request).read().decode('utf-8'))
                            if update_res_obj['success']:
                                update = True
                                host[ip_version] = public_ip
                                log('INFO','* update successful (type: {0}, fqdn: {1}'
                                      ', ip: {2})'.format(record_type, fqdn, public_ip))
                        except (Exception, HTTPError) as e:
                            log('ERROR', '* update failed (type: {0}, fqdn: {1}'
                                  ', ip: {2})'.format(record_type, fqdn, public_ip))

                # if any records were updated, update the config file accordingly
                if update:
                    print('* updates completed. bye.')
                    with open(config_file_name, 'w') as config_file:
                        json.dump(config, config_file, indent=1, sort_keys=True)
                else:
                    print('* nothing to update. bye.')


    except requests.exceptions.RequestException as e:
        log('ERROR', 'Request error: ' + str(e))
        time.sleep(interval)
        continue


