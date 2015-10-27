from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import courses
from canvas_sdk import RequestContext

course_id = 12345    # needs to be replace with real value

request_context = RequestContext(OAUTH_TOKEN, CANVAS_URL)

results = courses.list_your_courses(request_context, 'term')
for idx, course in enumerate(results.json()):
         print "course %d has data %s" % (idx, course)
