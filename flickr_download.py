#!/usr/bin/env python
#
# Util to download a full Flickr set.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import argparse
import errno
import logging
import os
import sys
import time

import flickr_api as Flickr
from flickr_api.flickrerrors import FlickrAPIError
from dateutil import parser
import yaml

CONFIG_FILE = "~/.flickr_download"
OAUTH_TOKEN_FILE = "~/.flickr_token"


def _init(key, secret, oauth):
    """
    Initialize API.

    @see: http://www.flickr.com/services/api/

    @param key: str, API key
    @param secret: str, API secret
    """
    Flickr.set_keys(key, secret)
    if not oauth:
        return True

    if os.path.exists(os.path.expanduser(OAUTH_TOKEN_FILE)):
        Flickr.set_auth_handler(os.path.expanduser(OAUTH_TOKEN_FILE))
        return True

    # Get new OAuth credentials
    auth = Flickr.auth.AuthHandler()  # creates the AuthHandler object
    perms = "read"  # set the required permissions
    url = auth.get_authorization_url(perms)
    print
    print("\nEnter the following url in a browser to authorize the application:")
    print(url)
    print("Copy and paste the <oauth_verifier> value from XML here and press return:")
    Flickr.set_auth_handler(auth)
    token = raw_input()
    auth.set_verifier(token)
    auth.save(os.path.expanduser(OAUTH_TOKEN_FILE))
    print("OAuth token was saved, re-run script to use it.")
    return False


def _load_defaults():
    """
    Load default parameters from config file

    @return: dict, default parameters
    """
    filename = os.path.expanduser(CONFIG_FILE)
    logging.debug('Loading configuration from {}'.format(filename))
    try:
        with open(filename, 'r') as cfile:
            vals = yaml.load(cfile.read())
            return vals
    except yaml.YAMLError as ex:
        logging.warning('Could not parse configuration file: {}'.format(ex))
    except IOError as ex:
        if ex.errno != errno.ENOENT:
            logging.warning('Could not open configuration file: {}'.format(ex))
        else:
            logging.debug('No config file')

    return {}


def download(user_id, fast_forward=False):
    """
    Download the set with 'set_id' to the current directory.

    @param set_id: str, id of the photo set
    @param size_label: str|None, size to download (or None for largest available)
    """
    suffix = ""
    user = Flickr.test.login()
    photos = []
    pagenum = 1
    while True:
        try:
            print('getting page {0}'.format(pagenum))
            page = user.getPhotos(user_id=user_id,per_page=500,page=pagenum)
            photos.extend(page)
            print(len(photos))
            pagenum += 1
	    if len(photos) % 500 != 0:
              break
        except FlickrAPIError as ex:
            if ex.code == 1:
                break
            raise
    
    for photo in photos:
        if fast_forward and is_similar_file('-{0}.jpg'.format(photo.id).replace('/', '-')):
            continue
        info = photo.getInfo()
        taken = parser.parse(info['taken'])
        taken_unix = time.mktime(taken.timetuple())
        fname = '{0}-{1}-{2}.jpg'.format(taken_unix, photo.title, photo.id).replace('/', '-')
        if os.path.exists(fname):
            # TODO: Ideally we should check for file size / md5 here
            # to handle failed downloads.
            print('Skipping {0}, as it exists already'.format(fname))
            continue

        print('Saving: {0}'.format(fname))
        try:
            photo.save(fname, None)
        except:
            time.sleep(5)
            photo.save(fname, None)

        # Set file times to when the photo was taken
        os.utime(fname, (taken_unix, taken_unix))


def is_similar_file(suffix):
    return len(filter(lambda filename: filename.endswith(suffix), os.listdir('.'))) > 0

def main():
    parser = argparse.ArgumentParser('Download a Flickr Set')
    parser.add_argument('-k', '--api_key', type=str,
                        help='Flickr API key')
    parser.add_argument('-u', '--user_id', type=str,
                        help='Flickr User ID')
    parser.add_argument('-s', '--api_secret', type=str,
                        help='Flickr API secret')
    parser.add_argument('--no_fast_forward', action='store_true',
			help='Don\'t check for the existance of all files by exact file name, skip some for performance')
    parser.set_defaults(**_load_defaults())

    args = parser.parse_args()

    if not args.api_key or not args.api_secret:
        print ('You need to pass in both "api_key" and "api_secret" arguments', file=sys.stderr)
        return 1

    ret = _init(args.api_key, args.api_secret, True)
    if not ret:
        return 1

    fast_forward = True
    if args.no_fast_forward:
        fast_forward = False

    download(args.user_id, fast_forward)

if __name__ == '__main__':
    sys.exit(main())
