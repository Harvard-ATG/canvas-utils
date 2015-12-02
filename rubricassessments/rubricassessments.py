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

logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    # Parse the CLI arguments
    parser = argparse.ArgumentParser(description='Gets assignment and submission data with rubric assessments for a given course.')
    parser.add_argument('course_id', type=int, help="The canvas course ID")
    args = parser.parse_args()
    
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
    student_results = transform_rubric_data(data)
    save_json(filename=transformed_json_filename, data=student_results)
    
    # Create a spreadsheet of the results by student
    save_rubric_spreadsheet(filename=spreadsheet_filename, student_results=student_results)
    
    logger.info("Done.")

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
    '''
    Loads all data needed to work with rubric assessments.
    '''
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

def transform_rubric_data(data):
    '''
    Transforms the raw rubric assessment data so that it's grouped by
    student.
    '''
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
    submissions_dict = dict([
        (s['assignment_id'], s['submissions']) 
        for s in data['submissions'] 
        if s['assignment_id'] in assignment_ids])

    # Group the assignments and rubric assessments by student
    # based on the existing submission data.
    by_student = {}
    for assignment in assignments:
        assignment_id = assignment['id']
        assignment_name = assignment['name']
        rubric_definition = assignment['rubric']
        for submission in submissions_dict.get(assignment_id, []):
            rubric_assessment = submission.get('rubric_assessment', None)
            user_id = submission['user_id']
            by_student.setdefault(user_id, {})
            by_student[user_id][assignment_id] = {
                'assignment_id': assignment_id,
                'assignment_name': assignment_name,
                'rubric': _merge_rubric(rubric_definition, rubric_assessment),
            }

    # Generate a complete list of students and their associated assignment
    # rubric assessments. If a student either did not submit the assignment,
    # or no rubric assessment was present, insert a blank rubric assessment
    # for the assignment. This ensures that every student has every assignment
    # and every assignment has a rubric assessment (blank or otherwise).
    student_results = []
    for student in students:
        user_id = student['id']
        user_name = student['sortable_name']
        student_assignments = []
        for assignment in assignments:
            assignment_id = assignment['id']
            assignment_name = assignment['name']
            rubric_definition = assignment['rubric']
            if user_id in by_student and assignment_id in by_student[user_id]:
                student_assignments.append(by_student[user_id][assignment_id])
            else:
                student_assignments.append({
                    'assignment_id': assignment_id,
                    'assignment_name': assignment_name,
                    'rubric': _merge_rubric(rubric_definition, None),
                })
        student_results.append({
            'user_id': user_id,
            'sortable_name': user_name,
            'data': student_assignments,
        })

    logger.info(json.dumps(student_results, sort_keys=True, indent=2, separators=(',', ': ')))

    return student_results

def _merge_rubric(rubric_definition, rubric_assessment):
    '''
    Helper function to merge a rubric definition and rubric assessment.
    '''
    result = []
    for criteria in rubric_definition:
        criteria_id = criteria['id']
        graded_criteria_comments = None
        graded_criteria_points = None
        if rubric_assessment is not None and criteria_id in rubric_assessment:
            graded_criteria = rubric_assessment[criteria_id]
            graded_criteria_comments = graded_criteria.get('comments', '')
            graded_criteria_points = graded_criteria.get('points', None)
        result.append({
            'description': criteria['description'],
            'comments': graded_criteria_comments,
            'points': graded_criteria_points,
        })
    return result


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

    # Formats/Styles
    bold_style = xlwt.easyxf('font: bold 1')
    right_align = xlwt.easyxf("align: horiz right")
    student_name_fmt = u'{sortable_name} ({user_id})'
    assignment_name_fmt = u'{assignment_name} ({assignment_id})'
    criteria_name_fmt = u'Criteria {num}: {description}'
    
    # Create workbook
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet('Assignments Sheet', cell_overwrite_ok=True)
    ws.write(0,0, u'Assignment \u2192'.encode('utf-8'), right_align)
    ws.write(1,0, u'Rubric \u2192'.encode('utf-8'), right_align)
    ws.write(2,0, u'Students \u2193'.encode('utf-8'))
    ws.col(0).width = 256 * max([len(student_name_fmt.format(**s)) for s in student_results])

    # Insert the worksheet data
    start_row, start_col = (3, 1)
    header_inserted = {'assignment':{},'criteria':{}}
    for user_idx, student in enumerate(student_results):
        user_row = start_row + user_idx
        ws.write(user_row, 0, student_name_fmt.format(**student))
        graded_assignments = student['data']
        assignment_col = start_col
        for assignment_idx, graded_assignment in enumerate(graded_assignments):
            criteria_col = assignment_col
            for criteria_idx, criteria in enumerate(graded_assignment['rubric']):
                ws.write(user_row, criteria_col, criteria['comments'])
                ws.write(user_row, criteria_col + 1, criteria['points'])
                if criteria_col not in header_inserted['criteria']:
                    criteria_label = criteria_name_fmt.format(num=criteria_idx+1, description=criteria['description'])
                    ws.write_merge(1, 1, criteria_col, criteria_col + 1, criteria_label)
                    ws.write(2, criteria_col, "Comments")
                    ws.write(2, criteria_col + 1, "Points")
                    header_inserted['criteria'][criteria_col] = True
                criteria_col += 2
            if assignment_col not in header_inserted['assignment']:
                assignment_name = assignment_name_fmt.format(**graded_assignment)
                ws.write_merge(0,  0, assignment_col, criteria_col - 1, assignment_name, bold_style)
                header_inserted['assignment'][assignment_col] = True
            assignment_col = criteria_col

    logger.info("Writing data to %s" % filename)
    wb.save(filename)


if __name__ == '__main__':
    main()