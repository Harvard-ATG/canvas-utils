#!/usr/bin/env python

import os
import sys
import re
import argparse
import requests
import json
import logging
import csv
from datetime import date, timedelta 
from collections import Counter
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# Holds global settings used throughout the script
SETTINGS = {
    # Course ID, supplied from CLI 
    "course_id": None, 

    # A list of enrollment types to return. Accepted values are: StudentEnrollment,TeacherEnrollment,
    # TaEnrollment,DesignerEnrollment,and ObserverEnrollment.If omitted, all enrollment types are returned. 
    "enrollment_types": [],

    # OAuth token needed to make requests to the canvas API, supplied from CLI or file
    "oauth_token": None,

    # Name of the file containing the oauth token 
    "oauth_file": "oauthtoken.txt",

    # API base url for making api requests
    "api_base_url": "https://canvas.harvard.edu/api/v1",

    # API defaults to 10 per page when returning paginated results (i.e. for User Page Views, Enrollment, etc)
    "api_per_page": 100, 

    # Date range for retrieving results (in ISO8601 format)
    "start_time": (date.today() - timedelta(90)).isoformat(),
    "end_time": date.today().isoformat(),

    # File names and formats for saving the results
    "csv_file_name": "pageviews_{course_id}_{start_time}-{end_time}.csv",
    "json_file_name": "pageviews_{course_id}_{start_time}-{end_time}.json",

    # File to save cache
    "cache_file": "cache-{hash}.json",
}

# Holds cached data
_CACHE = {} 

def read_oauth_token():
    '''Returns the oauth token contained in the config file.'''
    logger.debug("Reading OAuth token from file...")
    file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), SETTINGS['oauth_file'])
    if not os.path.exists(file_path):
        raise Exception("OAuth token not found in %s because it does not exist" % file_path)

    oauth_token = None
    with open(file_path) as f:
        oauth_token = f.read().strip()

    return oauth_token

def load_settings():
    '''Loads the script settings into the SETTINGS global variable.'''
    parser = argparse.ArgumentParser(description='Aggregates data about page views for a course in the Canvas LMS')
    parser.add_argument('course_id', type=int, help="The ID of the course object")
    parser.add_argument('--oauth_token', type=str, help="OAuth access token for Canavs API requests. Defaults to the value in %s (if present)." % SETTINGS['oauth_file'])
    parser.add_argument('--start_time', type=str, help="Start time ISO 8601 format YYYY-MM-DD. Defaults to 90 days ago.")
    parser.add_argument('--end_time', type=str, help="End time ISO 8601 format YYYY-MM-DD. Defaults to today.")
    parser.add_argument('--enrollment_types',  nargs='*',  default=[], help='Enrollment types to include: StudentEnrollment TeacherEnrollment TaEnrollment DesignerEnrollment ObserverEnrollment. If omitted, includes all types.')
    args = parser.parse_args()

    SETTINGS['course_id'] = args.course_id
    SETTINGS['enrollment_types'] = args.enrollment_types

    if args.oauth_token is not None:
        SETTINGS['oauth_token'] = args.oauth_token
    else:
        SETTINGS['oauth_token'] = read_oauth_token()

    if args.start_time is not None:
        SETTINGS['start_time'] = args.start_time

    if args.end_time is not None:
        SETTINGS['end_time'] = args.end_time

    logger.info("Loaded script settings")
    logger.debug("Settings: %s" % SETTINGS)

def cid():
    '''Convenience function used to return the course_id.'''
    return SETTINGS['course_id']

def jsonpp(jsondata):
    '''Convenience function to pretty print JSON.'''
    return json.dumps(jsondata, separators=(',',':'), indent=4, sort_keys=True)

def extract_header_links(link_header):
    '''
    Extracts the "Link:" header from the response and returns a dictionary mapping rel => url.

    See also: https://canvas.instructure.com/doc/api/file.pagination.html

    Parameters:
    - link_header: a string containing the value of the "Link" header

    Returns:
    - a dictionary mapping each link relationship to its corresponding URL
    '''
    result = {}
    if not link_header:
        return result 

    p = re.compile(ur'<([^<>]+)>;\s*rel="([^"]+)",?')
    matches = re.findall(p, link_header)
    result = {m[1]:m[0] for m in matches}

    logger.debug("Extracted header links=%s", result)

    return result


def api_url(url):
    '''Returns the full URL to use for making requests to the API, assuming it's not an absolute URL.'''
    if url.startswith('http'):
        return url
    return SETTINGS['api_base_url'] + url

def api_fetch_cache(f): 
    '''
    Decorator that wraps the api_fetch() function and returns values from the
    cache if available instead of calling the API.

    Note: this is a naive implementation to facilitate development
    '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        url = args[0]
        params = kwargs.get('params', None)
        _CACHE = f.func_globals['_CACHE']

        cache_key_str = url 
        if params is not None:
            cache_key_str = cache_key_str + "?" + "&".join([k+"="+str(params[k]) for k in params])

        cache_key = hashlib.md5(bytes(cache_key_str)).hexdigest()

        if cache_key in _CACHE:
            logger.info("Retrieved %s from cache with params=%s" % (url, params))
            logger.debug("Cache hit %s (%s)" % (cache_key, cache_key_str))
            return _CACHE[cache_key]["data"]
        else:
            logger.debug("Cache miss %s (%s)... fetching from API" % (cache_key, cache_key_str))
            result = f(*args, **kwargs)
            _CACHE[cache_key] = {"data": result, "key": cache_key_str}
            return result
    return wrapper

def file_cache_key():
    '''Returns a hash of the parameters for the data set.'''
    format_str = "{course_id}_{enrollment_types}_{start_time}_{end_time}"
    result_str = format_str.format(
        course_id=SETTINGS['course_id'], 
        enrollment_types="".join(SETTINGS['enrollment_types']), 
        start_time=SETTINGS['start_time'],
        end_time=SETTINGS['end_time'])
    return hashlib.md5(bytes(result_str)).hexdigest()

def save_cache():
    '''Writes out the cache to a file.'''
    cachefile = SETTINGS['cache_file'].format(hash=file_cache_key())
    logger.info("Saving cache to file %s..." % cachefile)
    with open(cachefile, "w") as f:
        f.write(json.dumps(_CACHE, separators=(',',':'), indent=4))

def load_cache():
    '''Loads the cache into memory.'''
    global _CACHE
    _CACHE = {}

    cachefile = SETTINGS['cache_file'].format(hash=file_cache_key())
    logger.info("Loading cache file %s" % cachefile)

    if os.path.exists(cachefile):
        with open(cachefile, "r") as f:
            result = f.read().strip()
            if result:
                _CACHE = json.loads(result)
        logger.info("Cache file loaded")
    else:
        logger.info("Cache file not found")

    logger.info("Cache has %s keys" % len(_CACHE))

@api_fetch_cache
def api_fetch(url, **kwargs):
    '''
    Fetches a resource from the Canvas API given a URL. Knows how to handle paginated
    results. Each page will be one data object in the list that is returned.

    Can be wrapped with the @api_fetch_cache decorator to proxy requests through
    a local cache of data objects.

    Parameters:
    - url: the API resource URL to request

    Optional keyword arguments:
    - params: a dictionary of parameters to include in the URL
    - response_data: an initial list of data objects to augment

    Returns:
    - A list of data objects
    '''
    # curl -H "Authorization: Bearer <ACCESS-TOKEN>" https://canvas.instructure.com/api/v1/courses
    headers = {'Authorization': 'Bearer %s' % SETTINGS['oauth_token']}
    request_url = api_url(url)
    params = kwargs.get('params', None)
    action = kwargs.get('action', None)
    response_data = []
    result = None
    has_next = True
    page_num = 0

    logger.info("\tRequest Initiated [url=%s]" % request_url)
    while has_next:
        page_num += 1
        r = requests.get(request_url, headers=headers, params=params)
        logger.info("\tRequest In Progress [page=%d] [request_url=%s] [response_code=%s]" % (page_num, r.url, r.status_code))
        logger.debug("Response headers=%s" % r.headers)

        if r.status_code == 200:
            logger.debug("\tResponse data=%s" % r.text)
            result = json.loads(r.text)
            response_data.append(result)
        else:
            logger.debug("\tNo response data")

        links = extract_header_links(r.headers.get('link'))
        has_next = 'next' in links
        if has_next:
            request_url = links['next']
            params = None # cleared params because link url is opaque

    if action is not None and hasattr(action, '__call__'):
        response_data = action(response_data)

    logger.info("\tRequest Completed [pages=%d] [total_size=%d]" % (page_num, sum([isinstance(p, list) and len(p) or 1 for p in response_data])))

    return response_data

def fetch_course():
    '''Fetches Course data from the API.'''
    url = '/courses/{course_id}'.format(course_id=cid())
    data = api_fetch(url)
    logger.debug("Course object=%s" % jsonpp(data))
    if len(data) == 1: 
        return data[0]
    return None

def fetch_course_enrollment():
    '''Fetches Course Enrollment data from the API.'''
    url = '/courses/{course_id}/enrollments'.format(course_id=cid())
    params = {'per_page': SETTINGS['api_per_page']} 
    if len(SETTINGS['enrollment_types']) > 0:
        params['type[]'] = SETTINGS['enrollment_types']
    data = api_fetch(url, params=params, action=reduce_enrollment)
    logger.debug("Course enrollment object=%s" % jsonpp(data))
    return data

def fetch_user_page_views(user_id, start_time, end_time):
    '''Fetches User Page View objects from the API for a given user and date range.'''
    url = '/users/{user_id}/page_views'.format(user_id=user_id)
    params = {
        "start_time": start_time, 
        "end_time": end_time, 
        "per_page": SETTINGS['api_per_page']
    }
    data = api_fetch(url, params=params, action=reduce_user_page_views)
    logger.debug("Page views for user_id=%s object=%s" % (user_id, jsonpp(data)))
    return data

def reduce_paginated_data(data, whitelist=None):
    '''
    Flattens (joins all pages into one giant page) and reduces (scrubs data not in the whitelist).
    When whitelist is None, data objects are not scrubbed. 
    '''
    if len(data) > 0:
        if whitelist is None:
            return reduce(lambda x, y: x + y, data, [])
        else:
            return reduce(lambda x, y: x + [{k:d.get(k,None) for k in whitelist} for d in y], data, [])
    return data

def reduce_enrollment(data):
    '''Returns a flattened enrollment list (not paginated).'''
    return reduce_paginated_data(data, ['id', 'course_id', 'user_id'])

def reduce_user_page_views(data):
    '''Returns a user page veiws list (not paginated).'''
    return reduce_paginated_data(data, ['id', 'url'])

def save_data(page_views_by_url, fmt="csv"):
    '''Saves data to a CSV or JSON file (defaults to CSV).'''
    start_time = SETTINGS["start_time"]
    end_time = SETTINGS["end_time"]
    if fmt == "csv":
        file_name = SETTINGS["csv_file_name"].format(**SETTINGS)
        with open(file_name, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["URL", "Page Views", "Start Time", "End Time"])
            for url, count in page_views_by_url.iteritems():
                writer.writerow([url, count, start_time, end_time])
    elif fmt == "json":
        file_name = SETTINGS["json_file_name"].format(**SETTINGS)
        with open(file_name, 'w') as jsonfile:
            jsondata = [];
            for url, count in page_views_by_url.iteritems():
                jsondata.append({
                    "url":url, 
                    "pageviews": count, 
                    "start_time": start_time, 
                    "end_time": end_time
                })
            jsonfile.write(jsonpp(jsondata))
    else:
        raise "Data format not supported: %s" % fmt

    logger.info("Saving data as %s to file %s..." % (fmt, file_name))

def is_course_url(course_id, url):
    '''Returns true if the URL is a valid course URL for the course ID.'''
    course_url = 'https://canvas.harvard.edu/courses/{course_id}'.format(course_id=cid())
    url = url.lower()
    return course_url == url or url.startswith(course_url + "/")

def main():
    '''Main script.'''
    load_settings()
    load_cache()

    logger.info("=> Fetching course data")
    course = fetch_course()
    course_id = cid()

    # If a user has multiple enrollments in a context (e.g. as a teacher and a
    # student or in multiple course sections), each enrollment will be listed
    # separately, so we need to get the set of unique users from the enrollment list.
    logger.info("=> Fetching enrolled users for course %s" % course_id)
    enrollment = fetch_course_enrollment()
    user_set = set([e['user_id'] for e in enrollment if e['user_id'] is not None])
    num_users = len(user_set)
    logger.info("=> Retrieved %d enrolled users for course %s" % (num_users, course_id))
    logger.debug("=> Enrolled users=%s" % sorted(list(user_set)))

    # Get each user's page views for the designated date range
    page_views_by_user = {}
    num_page_view_objects = 0
    for index, user_id in enumerate(user_set):
        logger.info("=> Fetching %d of %d user page views [user_id=%s]" % (index+1, num_users, user_id))
        result = fetch_user_page_views(user_id, SETTINGS['start_time'], SETTINGS['end_time'])
        if result is None:
            result = []
        else:
            num_page_view_objects += len(result)
        page_views_by_user[user_id] = result

    logger.info("=> Fetched %d of %d user page views with %d total objects" % (index+1, num_users, num_page_view_objects))
    logger.debug("=> Page views by user=%s" % jsonpp(page_views_by_user))

    # Get the total URL page views across the set of users for the course URL namespace
    page_views_by_url = Counter()
    logger.info("=> Counting total page views across users")
    for user_id, page_views in page_views_by_user.iteritems():
        for page_view in page_views:
            url = page_view['url']
            if is_course_url(course_id, url):
                count = page_views_by_url.setdefault(url, 0)
                page_views_by_url[url] = count + 1

    logger.info("=> Finished counting page views")
    #logger.info("Top 3 page views: %s" % page_views_by_url.most_common(3))
    logger.debug("=> Page views by URL: %s" % jsonpp(page_views_by_url))

    # Save the data
    logger.info("=> Saving data to files")
    save_data(page_views_by_url, 'csv')
    save_data(page_views_by_url, 'json')

    # Save the cache
    save_cache()

    logger.info("=> Done.")

    sys.exit()

# Execute the main function if this script is being called directly instead of imported
if __name__ == "__main__":
    main()
