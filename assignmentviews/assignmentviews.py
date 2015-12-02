from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import courses, users
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys
import os.path
import logging
import json
import argparse
import urlparse
import datetime

logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Gets assignment and submission data with rubric assessments for a given course.')
    parser.add_argument('course_id', type=int, help="The canvas course ID")
    args = parser.parse_args()

    course_id = args.course_id
    base_path = os.path.dirname(__file__)
    cache_json_filename = os.path.join(base_path, "%s.json" % course_id)

    data = None
    logger.info("Checking cache: %s" % cache_json_filename)
    if os.path.exists(cache_json_filename):
        logger.info("Loading data from file %s instead of fetching from %s" % (cache_json_filename, CANVAS_URL))
        with open(cache_json_filename, 'r') as f:
            data = json.load(f)
            data['_cache'] = False
    else:
        logger.info("Loading data from %s" % CANVAS_URL)
        data = load_data(course_id)
        data['_cache'] = True

    # Save the raw API data (i.e. cache it) since it's expensive to load
    if data['_cache'] is True:
        save_json(filename=cache_json_filename, data=data)

    logger.info("Done.")

def load_data(course_id):
    '''
    Loads the page views data.
    '''
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL)
    course_users = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")

    parsed_url = urlparse.urlparse(CANVAS_URL)
    course_url = "%s://%s/courses/%s" % (parsed_url.scheme, parsed_url.netloc, course_id)
    start_time, end_time = ("2015-01-01", "2015-06-15")

    page_views = []
    for user in course_users:
        user_id = user['id']
        results = get_all_list_data(request_context, users.list_user_page_views, user_id, start_time=start_time, end_time=end_time)
        logger.debug("Page views for user_id=%s results=%s" % (user_id, results))
        page_views.extend(results) # [r for r in results if r['url'].startswith(course_url)]

    data = {
        "course_users": course_users,
        "page_views": page_views,
    }
    return data

def save_json(filename=None, data=None):
    '''
    Saves the raw data to a JSON file.
    '''
    if filename is None:
        raise Exception("Filename is required")
    logger.info("Writing data to %s" % filename)
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, sort_keys=True, indent=2, separators=(',', ': '))


if __name__ == '__main__':
    main()