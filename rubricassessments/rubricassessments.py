from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import submissions, assignments, courses
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys
import os.path
import logging
import json
import argparse
import xlwt
import datetime

parser = argparse.ArgumentParser(description='Gets assignment and submission data with rubric assessments for a given course.')
parser.add_argument('course_id', type=int, help="The canvas course ID")
args = parser.parse_args()

logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_students_list(request_context, course_id):
    '''
    Returns a list of all students in the course.
    
    https://canvas.instructure.com/doc/api/courses.html#method.courses.users
    '''
    results = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")
    students = sorted([{"sortable_name":x['sortable_name'], "id": x['id']} for x in results], key=lambda x: x['sortable_name'])
    logger.debug("Students in course: %s" % students)
    return list(students)

def get_assignments_list(request_context, course_id):
    '''
    Returns a list of assignments for the course.

    https://canvas.instructure.com/doc/api/assignments.html#method.assignments_api.index 
    '''
    results = get_all_list_data(request_context, assignments.list_assignments, course_id, '')
    logger.debug("Assignments List: %s" % [r['id'] for r in results]) 
    return results

def get_submissions_with_rubric_assessments(request_context, course_id, assignment_ids):
    '''
    Returns the submission and rubric assessment data for each assignment.

    https://canvas.instructure.com/doc/api/submissions.html#method.submissions_api.index
    '''
    include = "rubric_assessment"
    results = []
    for assignment_id in assignment_ids:
        list_data = get_all_list_data(request_context, submissions.list_assignment_submissions_courses, course_id, assignment_id, include)
        logger.debug("Submissions for assignment %s: %s" % (assignment_id, list_data))
        results.append({
            "assignment_id": assignment_id,
            "submissions": list_data,
        })
    return results

def load_rubric_data(course_id):
    request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
    students = get_students_list(request_context, course_id)
    assignments = get_assignments_list(request_context, course_id)
    assignment_ids = [assignment['id'] for assignment in assignments]
    submissions = get_submissions_with_rubric_assessments(request_context, course_id, assignment_ids)
    data = {
        'assignments': assignments,
        'submissions': submissions,
        'students': students,
    }
    return data

def transform_data_by_student(data):
    if not ('assignments' in data and 'submissions' in data):
        raise Exception("missing 'assignments' and 'submissions' in data")

    # Setup students lookup by canvas user ID 
    students = data['students']
    students_dict = dict([(s['id'], s['sortable_name']) for s in students])

    # Filter assignments so we only consider those with rubrics
    # and can easily lookup an assignment by its ID.
    assignments = [a for a in data['assignments'] if 'rubric' in a]
    assignment_ids = [a['id'] for a in assignments]
    assignment_dict = dict([(a['id'], a) for a in assignments])
    
    # Setup submission lookup by assignment ID.
    submissions_dict = dict([(s['assignment_id'], s['submissions']) for s in data['submissions'] if s['assignment_id'] in assignment_ids])

    # Collect the rubric assessment data per assignment per student.
    # We want to end up with a structure like this:
    #
    # Student1
    #   Assignment1
    #       Rubric
    #           Criteria1
    #           Criteria2
    #           ...
    #           CriteriaN
    #   Assignment2
    #       ...
    # Student2
    #   ...
    by_student = {}
    for assignment_idx, assignment in enumerate(assignments):
        assignment_id = assignment['id']
        rubric = assignment['rubric']
        criteria_dict = dict([(criteria['id'], criteria) for criteria in rubric])
        submissions = []
        if assignment_id in submissions_dict:
            submissions = submissions_dict[assignment_id]
        
        for submission in submissions:
            rubric_assessment = None
            if 'rubric_assessment' in submission:
                rubric_assessment = submission['rubric_assessment']

            user_id = submission['user_id']
            if not user_id in by_student:
                by_student[user_id] = [None] * len(assignments)
            if by_student[user_id][assignment_idx] is None:
                by_student[user_id][assignment_idx] = {}
            
            graded_assignment = by_student[user_id][assignment_idx]
            graded_assignment.update({
                'assignment_id': assignment['id'],
                'assignment_name': assignment['name'],
                'rubric': [],
            })
            
            for criteria in rubric:
                criteria_id = criteria['id']
                graded_criteria_comments = None
                graded_criteria_points = None
                if rubric_assessment is not None and criteria_id in rubric_assessment:
                    graded_criteria = rubric_assessment[criteria_id]
                    graded_criteria_comments = graded_criteria['comments']
                    graded_criteria_points = graded_criteria['points']
                graded_assignment['rubric'].append({
                    'description': criteria['description'],
                    'comments': graded_criteria_comments,
                    'points': graded_criteria_points,
                })

    student_results = []
    for student in students:
        user_id = student['id']
        user_name = student['sortable_name']
        if user_id not in by_student:
            continue
        student_results.append({
            'user_id': user_id,
            'sortable_name': user_name,
            'data': by_student[user_id],
        })

    logger.info(json.dumps(student_results, sort_keys=True, indent=2, separators=(',', ': ')))

    return student_results

def save_json(filename=None, data=None):
    '''
    Saves the raw data to a JSON file.
    '''
    if filename is None:
        raise Exception("Filename is required")
    logger.info("Writing data to %s" % filename)
    with open(filename, 'w') as outfile:
        json.dump(data, outfile, sort_keys=True, indent=2, separators=(',', ': '))

def save_rubric_spreadsheet(filename=None, student_results=None):
    '''
    Saves the rubric data to a spreadsheet.
    '''
    if filename is None:
        raise Exception("Filename is required")

    # Create workbook
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Assignments Sheet', cell_overwrite_ok=True)
    ws.write(0,0, "Project")
    ws.write(1,0, "Rubric")
    ws.write(2,0, "Students")

    start_row, start_col = (3, 1)
    for user_idx, student in enumerate(student_results):
        user_id = student['user_id']
        user_name = student['sortable_name']

        user_row = start_row + user_idx
        ws.write(user_row, 0, "%s (%s)" % (user_name, user_id))

        graded_assignments = student['data']
        assignment_col = start_col
        for assignment_idx, graded_assignment in enumerate(graded_assignments):
            if graded_assignment is None:
                continue
            assignment_name = "%s (%s)" % (graded_assignment['assignment_name'], graded_assignment['assignment_id'])
            ws.write(0,  assignment_col, assignment_name)

            criteria_col = assignment_col
            for criteria_idx, criteria in enumerate(graded_assignment['rubric']):
                criteria_label = "Criteria %s: %s" % (criteria_idx + 1, criteria['description'])
                ws.write(1, criteria_col, criteria_label)
                ws.write(2, criteria_col, "Comments")
                ws.write(2, criteria_col + 1, "Points")
                ws.write(user_row, criteria_col, criteria['comments'])
                ws.write(user_row, criteria_col + 1, criteria['points'])
                criteria_col += 2
            assignment_col = criteria_col

    logger.info("Writing data to %s" % filename)
    wb.save(filename)


# Get the data from local cache or Canvas API
course_id = args.course_id
base_path = os.path.dirname(__file__)
cache_json_filename = os.path.join(base_path, "%s.json" % course_id)
transformed_json_filename = os.path.join(base_path, "%s-transformed.json" % course_id)
spreadsheet_filename = os.path.join(base_path, "%s.xls" % course_id)

data = None
logger.info("Checking cache: %s" % cache_json_filename)
if os.path.exists(cache_json_filename):
    logger.info("Loading data from file %s instead of fetching from %s" % (cache_json_filename, CANVAS_URL))
    with open(cache_json_filename, 'r') as f:
        data = json.load(f)
        data['_cache'] = False
else:
    logger.info("Loading data from %s" % CANVAS_URL)
    data = load_rubric_data(course_id)
    data['_cache'] = True

# Save the raw API data (i.e. cache it) since it's expensive to load
if data['_cache'] is True:
    save_json(filename=cache_json_filename, data=data)

# Transform the data to a per-student assignment results (rubric assessments)
student_results = transform_data_by_student(data)
save_json(filename=transformed_json_filename, data=student_results)

# Create a spreadsheet of the results by student
save_rubric_spreadsheet(filename=spreadsheet_filename, student_results=student_results)

logger.info("Done.")