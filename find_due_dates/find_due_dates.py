from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import accounts, assignments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import logging
import argparse
import json
import xlwt
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

def save_spreadsheet(filename=None, data=None):
    if filename is None:
        raise Exception("Filename is required")
    if data is None:
        raise Exception("Data is required")

    courses = data['courses']
    assignments = data['assignments']

    # Formats/Styles
    bold_style = xlwt.easyxf('font: bold 1')
    right_align = xlwt.easyxf("align: horiz right")
    course_name_fmt = u'{name} ({id})'
    assignment_name_fmt = u'{name} ({id})'
    due_at_fmt = u'{due_at}'
    
    # Create workbook
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet('Due Dates Sheet', cell_overwrite_ok=True)
    ws.write(0,0, u'Term'.encode('utf-8'), bold_style)
    ws.write(0,1, u'Course'.encode('utf-8'), bold_style)
    ws.write(0,2, u'Assignment'.encode('utf-8'), bold_style)
    ws.write(0,3, u'Due Date'.encode('utf-8'), bold_style)
    
    # Write data to worksheet
    row = 1
    for course_idx, course in enumerate(courses):
        course_id= str(course['id'])
        course_assignments = assignments[course_id]
        for assignment_idx, assignment in enumerate(course_assignments):
            ws.write(row, 0, course['term']['name'])
            ws.write(row, 1, course_name_fmt.format(**course))
            ws.write(row, 2, assignment_name_fmt.format(**assignment))
            ws.write(row, 3, due_at_fmt.format(**assignment))
            row += 1
    
    # Save workbook
    logger.info("Saving spreadsheet to %s" % filename)
    wb.save(filename)

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
        
data = load_data()
print_statistics(data)
save_spreadsheet(filename='duedates.xls', data=data)
exit(0)
