from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import courses
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import sys

# Get the course ID from the CLI arguments
course_id = sys.argv[1]
if course_id is None:
    course_id = "dummy"

# Setup the request context with a large pagination limit to limit the total number of request
# needed for larger courses
request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL, per_page=1000)

# Note: need to use get_all_list_data() to follow the paged results that
# the canvas API returns.
results = get_all_list_data(request_context, courses.list_users_in_course_users, course_id, "email", enrollment_type="student")

# Extract and sort the results we want. 
users = sorted([(x['email'], x['name']) for x in results], key=lambda x: x[0])

# Print the names ane emails in CSV foramt
for idx, user in enumerate(users):
    print "%s,%s" % user
