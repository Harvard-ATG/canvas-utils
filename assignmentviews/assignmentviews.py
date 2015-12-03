from settings.secure import OAUTH_TOKEN, CANVAS_URL, TEST_CANVAS_URL
from canvas_sdk.methods import courses, users
from canvas_sdk.utils import get_all_list_data
from canvas_sdk.exceptions import CanvasAPIError
from canvas_sdk import RequestContext
import sys
import os.path
import logging
import json
import argparse
import urlparse
import datetime
import csv

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
    parser.add_argument('--randomized_students_csv', type=str, help="CSV file that maps students to random numbers", required=False)
    args = parser.parse_args()

    course_id = args.course_id
    randomized_students_csv = args.randomized_students_csv
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

    process_data(data, randomized_students_csv)

    logger.info("Total enrollment: %s" % len(data['enrollment']))
    logger.info("Total page views: %s" % len(data['page_views']))
    logger.info("Done.")

def load_data(course_id):
    '''
    Load page views for all users in a course.
    '''
    enrollment = get_students(course_id)
    user_ids = [user['id'] for user in enrollment]
    user_profiles = get_user_profiles(user_ids)
    page_views = get_page_views(course_id, user_ids)
    data = {
        "enrollment": enrollment,
        "user_profiles": user_profiles,
        "page_views": page_views,
    }
    return data

def process_data(data, randomized_students_csv):
    '''
    Process the data.
    '''
    logger.info("Processing data.")
    randomized_students = get_randomized_students(randomized_students_csv)
    
def get_randomized_students(csv_file_name):
    '''
    Returns a dictionary mapping a student's huid to a random ID.
    The random ID is what we'll return to the client, not the HUID to identify students.
    '''
    randomized_students = {}
    with open(csv_file_name, 'rb') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            random_id = row[0]
            first_name = row[1]
            last_name = row[2]
            huid = row[3]
            if random_id.isdigit():
                randomized_students[huid] = random_id
    logger.debug("Randomized students: number of random_ids=%s mapping=%s" % (len(randomized_students.keys()), randomized_students))
    return randomized_students

def get_students(course_id):
    '''
    Get the student enrollment from TEST environment because the course must be
    unconcluded and/or enrollment active. Since we can't unconclude the course
    in production, we need to do it in TEST and then hit that API endpoint.
    '''
    request_context = RequestContext(OAUTH_TOKEN, TEST_CANVAS_URL, per_page=100)
    result = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")
    return result

def get_user_profiles(user_ids):
    '''
    Get the user profiles for each user.
    '''
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL)
    user_profiles = []
    for user_id in user_ids:
        user_profile = users.get_user_profile(request_context, user_id)
        user_profiles.append(user_profile.json())
    return user_profiles

def get_page_views(course_id, user_ids):
    '''
    Get the page views from the PROD environment because the page views aren't
    synced over to the TEST environment.
    '''
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
    parsed_url = urlparse.urlparse(CANVAS_URL)
    course_url = "%s://%s/courses/%s" % (parsed_url.scheme, parsed_url.netloc, course_id)
    start_time, end_time = ("2015-01-01", "2015-06-15")

    page_views = []
    for user_id in user_ids:
        try:
            results = get_all_list_data(request_context, users.list_user_page_views, user_id, start_time=start_time, end_time=end_time)
        except CanvasAPIError as e:
            logger.error(str(e))
        logger.debug("Page views for user_id=%s results=%s" % (user_id, results))
        if results:
            page_views.extend([r for r in results if r and r.get('url','').startswith(course_url)])

    return page_views

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
