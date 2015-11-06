from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import courses
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys

# Get the course ID from the command line
course_id = sys.argv[1]
if course_id is None:
    sys.exit("Error: missing course_id")

# Setup the request context with a large pagination limit (minimize # of requests)
request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=100)

# NOTE: you must use get_all_list_data() in order to follow the paginated results
# and get all the data.
#
# If you just call the method directly, you'll get a single page (max 100 results)
# which may or may not include everyone if there are >100 students in the course.
results = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")

# Extract and sort the results we want. 
users = sorted([(x['email'], x['name']) for x in results], key=lambda x: x[0])

# Print the names and emails in CSV foramt
for idx, user in enumerate(users):
    print "%s,%s" % user
