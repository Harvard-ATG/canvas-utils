from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import accounts, assignments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import logging
import argparse
import json
import os.path

logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description='Find due dates set during a given period.')
parser.add_argument('account_id', help="Account ID used to find courses")
parser.add_argument('--enrollment_term_id', help="Enrollment Term ID to filter courses to given term.")
parser.add_argument('--start_date', help="Start date ISO8601 (YYYY-MM-DD)")
parser.add_argument('--end_date', help="End date ISO8601 (YYYY-MM-DD)")
args = parser.parse_args()
logger.debug("Arguments: %s" % args)

request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)

def load_data():
    cache_file = 'cache.json'
    data = {}
    if os.path.isfile(cache_file):
        logger.debug("Loading data from cache %s..." % cache_file)
        with open(cache_file, 'r') as f:
            data = json.loads(f.read().strip())
    
    # Fetch All Courses in Account
    if 'courses' not in data:
        logger.debug("Courses not in cache, so fetching from API")
        extra_kwargs = {"include": "term"}
        if args.enrollment_term_id:
            extra_kwargs.update({'enrollment_term_id': args.enrollment_term_id})
        result = get_all_list_data(request_context, accounts.list_active_courses_in_account, args.account_id, **extra_kwargs)
        courses = sorted(result, key=lambda c: c['name'])
        courses = [c for c in courses if c['workflow_state'] != 'unpublished']
        data['courses'] = courses
        with open(cache_file, 'w') as f:
            logger.debug("Writing courses to cache")
            f.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))
    
    # Fetch All Assignments for Each Course
    if 'assignments' not in data:
        logger.debug("Assignments not in cache, so fetching from API")
        data['assignments'] = {}
        for course in data['courses']:
            course_id = course['id']
            result = get_all_list_data(request_context, assignments.list_assignments, course_id, include="")
            data['assignments'][course_id] = result
        with open(cache_file, 'w') as f:
            logger.debug("Writing assignments to cache")
            f.write(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))
    
    return data

def print_statistics(data):
    # Output data
    print "Published course in account %s: %d" % (args.account_id, len(data['courses']))
    print "Course names:"
    for course in data['courses']:
        course_id = str(course['id'])
        print "%s - %s - %s" % (course['term']['name'], course_id, course['name'])
        print "\tTotal Assignments: %d" % len(data['assignments'][course_id])
        for assignment in sorted(data['assignments'][course_id], key=lambda a: a['due_at'], reverse=True):
            print "\tDue: %s -- %s" % (assignment['due_at'], assignment['name'])
        

print_statistics(load_data())
exit(0)
