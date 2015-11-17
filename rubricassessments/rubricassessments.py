from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import submissions, assignments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
from collections import OrderedDict
import sys
import logging
import json
import pprint

pp = pprint.PrettyPrinter(indent=2)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup Logging so we can see the API requests as they happen
logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# Get the course ID from the command line
course_id = None
if len(sys.argv) == 2:
    course_id = sys.argv[1]
else:
    sys.exit("Error: missing course_id")

def get_assignments_list(request_context, course_id):
    results = get_all_list_data(request_context, assignments.list_assignments, course_id, '')
    logger.debug("Assignments List: %s" % results) 
    return results

def get_rubric_assessments(request_context, course_id, assignment_ids):
    request_params = OrderedDict([ 
        ("course_id", course_id),
        ("student_ids", 'all'),
        ("assignment_ids", assignment_ids),
        ("grouped", False),
        ("include", "rubric_assessment"),
    ])
    results = get_all_list_data(request_context, submissions.list_submissions_for_multiple_assignments_courses, *request_params.values())
    logger.debug("Rubric Assessments: %s" % results)
    return results

request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)
assignments = get_assignments_list(request_context, course_id)
assignment_ids = [a['id'] for a in assignments]
rubric_assessments = get_rubric_assessments(request_context, course_id, assignment_ids)

results = {
    'Assignments': assignments,
    'Assignments Total': len(assignments),
    'Rubric Assessments': rubric_assessments,
    'Rubric Assessments Total': len(rubric_assessments),
}

print json.dumps(results, sort_keys=True, indent=2, separators=(',', ': '))
