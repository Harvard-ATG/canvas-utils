from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import submissions, assignments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys
import logging
import json

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

# Setup Logging so we can see the API requests as they happen
logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Get the course ID from the command line
course_id = None
if len(sys.argv) == 2:
    course_id = sys.argv[1]
else:
    sys.exit("Error: missing course_id")

# Get the data from the Canvas API
request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
assignments = get_assignments_list(request_context, course_id)
assignment_ids = [a['id'] for a in assignments]
submissions = get_submissions_with_rubric_assessments(request_context, course_id, assignment_ids)

# Format and output the data
filename = "{course_id}.json".format(course_id=course_id)
logger.info("Writing data to %s" % filename)
with open(filename, 'w') as outfile:
    results = {
        'Assignments': assignments,
        'Submissions': submissions,
    }
    json.dump(results, outfile, sort_keys=True, indent=2, separators=(',', ': '))
logger.info("Done.")
