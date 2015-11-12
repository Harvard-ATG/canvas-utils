from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import courses, users
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys
import pprint

pp = pprint.PrettyPrinter(indent=2)

# Get the course ID from the command line
course_id = None
if len(sys.argv) == 2:
    course_id = sys.argv[1]
else:
    sys.exit("Error: missing course_id")

# Setup the request context with a large pagination limit (minimize # of requests)
request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL)

# NOTE: you must use get_all_list_data() in order to follow the paginated results
# and get all the data.
#
# If you just call the method directly, you'll get a single page (max 100 results)
# which may or may not include everyone if there are >100 students in the course.

#response = courses.list_users_in_course_users(request_context, course_id, "email", enrollment_type="student")

results = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")

user_ids = [r['id'] for r in results]
users_page_views = []

for user_id in user_ids:
    results = get_all_list_data(request_context, users.list_user_page_views, user_id, start_time="2015-01-01", end_time="2015-06-15")
    user_page_views = []
    for result in results:
        if result['url'].startswith("https://canvas.harvard.edu/courses/%s" %course_id):
            user_page_views.append(result)
    users_page_views.extend(user_page_views)

pp.pprint(users_page_views)
