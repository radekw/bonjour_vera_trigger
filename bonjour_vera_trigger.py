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
        status = None
    return status

##############################################################################
def check_devices():
    all_available = False
    
    def browse_callback(sdRef, flags, interfaceIndex, errorCode,
                        serviceName, regtype, replyDomain):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return
        if not (flags & pybonjour.kDNSServiceFlagsAdd):
            print 'rmv: %s' % (serviceName)
        else:
            print 'add: %s' % (serviceName)
    
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = config['bonjour_type'],
                                              callBack = browse_callback)
    
    try:
        while True:
            ready = select.select([browse_sdRef], [], [], 15)
            if browse_sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(browse_sdRef)
    except KeyboardInterrupt:
        pass
    finally:
        browse_sdRef.close()
    
    return all_available

##############################################################################
def check_devices_forver():
    logging.error('not implemented yet')

##############################################################################
def main():
    global options, config
    
    parser = OptionParser(usage='Usage: %prog [options]\n')
    
    # funtionality options
    parser.add_option('-c', '--config', default=None,
                      action='store', type='string', dest='config',
                      help='Configuration file')
    parser.add_option('-d', '--daemon', dest='daemon',
                      action='store_true', default=False,
                      help='Run as daemon')
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
            print('ERROR: configuration file %s does not exist' %
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
    
    if options.daemon:
        while True:
            check_devices_forver()
    else:
        check_devices()

##############################################################################
if __name__ == "__main__":
    main()

##############################################################################
