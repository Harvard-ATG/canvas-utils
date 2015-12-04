from settings.secure import OAUTH_TOKEN, CANVAS_URL, TEST_CANVAS_URL
from canvas_sdk.methods import courses, users, assignments
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
import re
import csv
import xlwt

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
    parser.add_argument('--anonymized_students_csv', type=str, help="CSV file that maps student HUID's to random identifiers to anonymize the data", required=False)
    parser.add_argument('--start_time', type=str, help="Start time ISO 8601 format YYYY-MM-DD.")
    parser.add_argument('--end_time', type=str, help="End time ISO 8601 format YYYY-MM-DD.")
    args = parser.parse_args()

    course_id = args.course_id
    anonymized_students_csv = args.anonymized_students_csv
    start_time = args.start_time
    end_time = args.end_time
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
        data = load_data(course_id, start_time=start_time, end_time=end_time)
        data['_cache'] = True

    # Save the raw API data (i.e. cache it) since it's expensive to load
    if data['_cache'] is True:
        save_json(filename=cache_json_filename, data=data)
    
    # Check if the user provided a CSV file mapping a student's HUID to a random ID
    anonymized_students = None
    if anonymized_students_csv:
        anonymized_students = get_anonymized_students(anonymized_students_csv)

    # Process the data
    process_data(data, anonymized_students=anonymized_students)

    logger.info("Total enrollment: %s" % len(data['enrollment']))
    logger.info("Total page views: %s" % len(data['page_views']))
    logger.info("Done.")

def load_data(course_id, start_time=None, end_time=None):
    '''
    Load page views for all users in a course.
    '''
    course_enrollment = get_students(course_id)
    course_assignments = get_assignments(course_id)
    user_ids = [user['id'] for user in course_enrollment]
    user_profiles = get_user_profiles(user_ids)
    page_views = get_page_views(course_id, user_ids, start_time=start_time, end_time=end_time)
    
    data = {
        "course_id": course_id,
        "enrollment": course_enrollment,
        "assignments": course_assignments,
        "user_profiles": user_profiles,
        "page_views": page_views,
    }

    return data

def process_data(data, anonymized_students=None):
    '''
    Process the data.
    '''
    logger.info("Processing data.")
    create_page_views_xls(data, anonymized_students)
    
def get_anonymized_students(csv_file_name):
    '''
    Returns a dictionary mapping a student's HUID to a random ID.
    The random ID is going to be used to anonymize the data that is returned to the client.
    '''
    anonymized_students = {}
    with open(csv_file_name, 'rb') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            random_id = row[0]
            first_name = row[1]
            last_name = row[2]
            huid = row[3]
            if random_id.isdigit():
                anonymized_students[huid] = random_id
    logger.debug("Randomized students: number of random_ids=%s mapping=%s" % (len(anonymized_students.keys()), anonymized_students))
    return anonymized_students

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

def get_assignments(course_id):
    '''
    Returns a list of the assignments for the course.
    '''
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
    result = get_all_list_data(request_context, assignments.list_assignments, course_id, '')
    return result

def get_page_views(course_id, user_ids, start_time=None, end_time=None):
    '''
    Get the page views from the PROD environment because the page views aren't
    synced over to the TEST environment.
    '''
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
    course_url = _get_canvas_course_url(CANVAS_URL, course_id)
    date_range = {}
    if start_time is not None:
        date_range['start_time'] = start_time
    if end_time is not None:
        date_range['end_time'] = end_time

    page_views = []
    for user_id in user_ids:
        try:
            results = get_all_list_data(request_context, users.list_user_page_views, user_id, **date_range)
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

def create_page_views_xls(data, anonymized_students):
    '''
    Creates a spreadsheet containing the raw page views data
    '''
    course_id = data['course_id']
    page_views = data['page_views']

    filename = "%s-pageviews.xls" % course_id
    huid_of = _get_huid_of_user_dict(data['user_profiles'])
    course_url = _get_canvas_course_url(CANVAS_URL, course_id)
    assignment_url = course_url + '/assignments'
    assignment_of = _get_assignment_by_id_dict(data['assignments'])
    assignment_re = re.compile(assignment_url + '/(\d+)')
    
    # Formats/Styles
    bold_style = xlwt.easyxf('font: bold 1')
    
    # Create workbook
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet('Page Views')
    
    # Header row
    header_cols = ['PageView_Id','Student_Random_Id','Assignment_Id','Assignment_Name',
                   'Request_Date','Request_Url','Interaction_Seconds', 'UserAgent']
    max_col_widths = [len(header) for header in header_cols]

    # Body Rows
    row_data = []
    for page_view in page_views:
        request_url = page_view['url']
        if not request_url.startswith(course_url + '/assignments/'):
            continue
        if 'links' not in page_view or 'user' not in page_view['links']:
            continue
    
        user_id = page_view['links']['user']
        if user_id not in huid_of:
            continue

        huid = huid_of[user_id]
        if anonymized_students is None:
            student_random_id = huid
        else:
            if huid in anonymized_students:
                student_random_id  = anonymized_students[huid]
            else:
                continue

        page_view_id = page_view['id']
        request_date = page_view['created_at']
        user_agent = page_view['user_agent']
        interaction_seconds = page_view['interaction_seconds']
        m = assignment_re.search(request_url)
        assignment_id = ''
        assignment_name = ''
        if m is not None:
            assignment_id = int(m.group(1))
            if assignment_id in assignment_of:
                assignment_name = assignment_of[assignment_id]['name']
        if 'Video' not in assignment_name:
            continue

        row_values = [page_view_id, student_random_id, assignment_id, assignment_name, request_date, request_url, interaction_seconds, user_agent]
        row_data.append(row_values)
        for col_idx, value in enumerate(row_values):
            if len(str(value)) > max_col_widths[col_idx]:
                max_col_widths[col_idx] = len(str(value))       

    # Insert Header Row
    for col_idx, header_col in enumerate(header_cols):
        ws.write(0, col_idx, header_col, bold_style)

    # Insert Body Rows
    sorted_row_data = sorted(row_data, key=lambda r: (r[1], r[2], r[4]))
    for row_idx, row in enumerate(sorted_row_data):
        for col_idx, col_value in enumerate(row):
            ws.write(row_idx+1, col_idx, col_value)

    # Adjust column widths
    for col_idx, col_width in enumerate(max_col_widths):
        ws.col(col_idx).width = 256 * col_width
    
    # Save spreadsheet
    wb.save(filename)
    logger.info("Saved %s" % filename)

def _get_huid_of_user_dict(user_profiles):
    '''
    Returns a mapping of the Canvas user ID to the user's HUID.
    '''
    return dict([ (p['id'], p['login_id']) for p in user_profiles ])

def _get_canvas_course_url(canvas_api_url, course_id):
    '''
    Returns a course URL like http://canvas.domain/courses/:id
    based on the canvas API url.
    '''
    parsed_url = urlparse.urlparse(canvas_api_url)
    course_url = "%s://%s/courses/%s" % (parsed_url.scheme, parsed_url.netloc, course_id)
    return course_url

def _get_assignment_by_id_dict(course_assignments):
    '''
    Returns a mapping of course assignment IDs to course assignment objects.
    '''
    return dict([ (a['id'], a) for a in course_assignments])

if __name__ == '__main__':
    main()
