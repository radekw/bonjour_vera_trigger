#!/usr/bin/python

import os, sys, time, select, logging, subprocess, urllib2, json
from optparse import OptionParser

import pybonjour

from yaml import load
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

##############################################################################
options = None
config = {}
last_seen = time.time()

##############################################################################
def run_wait(cmd):
    logging.debug('executing: %s' % cmd)
    p = subprocess.Popen(cmd, shell=True, env=os.environ, 
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stdout, stderr) = p.communicate()
    return (p.returncode, stdout)

##############################################################################
def open_url(url):
    try:
        r = urllib2.urlopen(url, timeout=10)
        o = r.read()
    except urllib2.HTTPError, e:
        logging.error('HTTP_ERROR: %s (%s)' % (e.code, e.msg))
        return None
    except urllib2.URLError, e:
        logging.error('URL_ERROR: %s' % e.reason)
        return None
    except:
        logging.exception('ERROR: exception')
        return None
    return o

##############################################################################
def get_device_status_from_json(json_string):
    data = json.loads(json_string)
    status = None
    try:
        for k in data.keys():
            if k.find('Device_Num_') == 0:
                for s in data[k]['states']:
                    if s['variable'] == 'Status':
                        status = s['value']
    except:
        status = 0
    return status

##############################################################################
def trigger(available):
    if available:
        logging.info('triggering vera_triggers -> available')
        devices = config['vera_triggers']['available']
    else:
        logging.info('triggering vera_triggers -> not_available')
        devices = config['vera_triggers']['not_available']
    
    for dev in devices:
        if dev['id'] == 'lu_action' and dev['action'] == 'SetTarget':
            url = '%s/data_request?output_format=json' % config['vera_url']
            status_url = '%s&id=status&DeviceNum=%s' % (url, dev['DeviceNum'])
            action_url = url
            for k, v in dev.items():
                action_url += '&%s=%s' % (k, v)
            logging.debug('accessing status_url: %s' % status_url)
            status_json = open_url(status_url)
            if status_json is None:
                break
            status = get_device_status_from_json(status_json)
            logging.debug('status: current: %s; requested: %s' % \
                          (status, dev['newTargetValue']))
            if str(status) == str(dev['newTargetValue']):
                logging.info('no action on DeviceNum %s' % dev['DeviceNum'])
                break
            logging.info('triggering DeviceNum %s' % dev['DeviceNum'])
            logging.debug('accessing action_url: %s' % action_url)
            open_url(action_url)

##############################################################################
def check_devices():
    global last_seen
    device_present = False
    
    def browse_callback(sdRef, flags, interfaceIndex, errorCode,
                        serviceName, regtype, replyDomain):
        global last_seen
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return
        device_name = serviceName.split('@')[0]
        if device_name not in config['devices_names']:
            logging.debug('unknown device: %s' % device_name)
            return
        logging.info('known device: %s' % device_name)
        last_seen = time.time()
    
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = config['bonjour_type'],
                                              callBack = browse_callback)
    
    try:
        while True:
            ready = select.select([browse_sdRef], [], [], 15)
            if browse_sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(browse_sdRef)
            device_present = False
            last_seen_ago = int(time.time() - last_seen)
            logging.debug('last seen %s seconds ago' % last_seen_ago)
            if time.time() - last_seen <= 180:
                device_present = True
            logging.debug('device_present: %s' % device_present)
            if not options.test_only:
                trigger(device_present)
            logging.debug('')
    except KeyboardInterrupt:
        logging.info('interrupted - exiting')
    finally:
        browse_sdRef.close()
    
    return device_present

##############################################################################
def main():
    global options, config
    
    parser = OptionParser(usage='Usage: %prog [options]\n')
    
    # funtionality options
    parser.add_option('-c', '--config', default=None,
                      action='store', type='string', dest='config',
                      help='Configuration file')
    parser.add_option('-t', '--test', dest='test_only',
                      action='store_true', default=False,
                      help='Test only')
    parser.add_option('-v', '--verbose', dest='verbose',
                      action='store_true', default=False,
                      help='Update its own record')
    (options, args) = parser.parse_args()
    
    # configure logging
    log_level = logging.INFO
    if options.verbose:
        log_level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%y/%m/%d %H:%M:%S',
                        level=log_level)
    
    # read configuration file
    if options.config:
        if os.path.exists(options.config):
            config = load(file(options.config, 'r'), Loader=Loader)
        else:
            logging.error('ERROR: configuration file %s does not exist' %
                  options.config)
            sys.exit(1)
    else:
        cfn = 'bonjour_vera_trigger.yaml'
        for config_file in [os.path.join('/', 'etc', cfn),
                            os.path.expanduser('~/.%s' % cfn),
                            os.path.join(os.path.dirname(__file__), cfn)]:
            if os.path.exists(config_file):
                config = load(file(config_file, 'r'), Loader=Loader)
                break
    
    check_devices()

##############################################################################
if __name__ == "__main__":
    main()

##############################################################################
