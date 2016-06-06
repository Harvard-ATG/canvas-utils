from settings.secure import OAUTH_TOKEN, CANVAS_URL
from canvas_sdk.methods import accounts, assignments
from canvas_sdk.utils import get_all_list_data
from canvas_sdk import RequestContext
import logging
import argparse
import json
import datetime
import dateutil.parser
import dateutil.tz
import os.path
import xlwt

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
parser.add_argument('--reading_period_start', help="Start date for reading period. Example: 2016-04-28")
parser.add_argument('--reading_period_end', help="end date for reading period. Example: 2016-05-04")
parser.add_argument('--exam_period_start', help="Start date for exam period. Example: 2016-05-05")
parser.add_argument('--exam_period_end', help="end date for exam period. Example: 2016-05-14")
args = parser.parse_args()
logger.debug("Arguments: %s" % args)

UTC_TZ = dateutil.tz.gettz('UTC')
EST_TZ = dateutil.tz.gettz('America/New_York')

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
    
    # Worksheet 1   
    if args.reading_period_start and args.reading_period_end:
        reading_period_start = datetime.datetime.strptime(args.reading_period_start, "%Y-%m-%d").replace(tzinfo=EST_TZ)
        reading_period_end = datetime.datetime.strptime(args.reading_period_end, "%Y-%m-%d").replace(tzinfo=EST_TZ)
        reading_period_delta = reading_period_end - reading_period_start + datetime.timedelta(1)
        reading_period_dates = [reading_period_start + datetime.timedelta(i) for i in range(reading_period_delta.days)]
        reading_period_date_col = {d.strftime('%Y-%m-%d'):4+idx for idx, d in enumerate(reading_period_dates)}
        reading_period_str_range = '%s - %s' % (reading_period_start.strftime('%m/%d/%Y'), reading_period_end.strftime('%m/%d/%Y'))

        exam_period_start = datetime.datetime.strptime(args.exam_period_start, "%Y-%m-%d").replace(tzinfo=EST_TZ)
        exam_period_end = datetime.datetime.strptime(args.exam_period_end, "%Y-%m-%d").replace(tzinfo=EST_TZ)
        exam_period_delta = exam_period_end - exam_period_start + datetime.timedelta(1)
        exam_period_dates = [exam_period_start + datetime.timedelta(i) for i in range(exam_period_delta.days)]
        exam_period_date_col = {d.strftime('%Y-%m-%d'):max(reading_period_date_col.values())+1+idx for idx, d in enumerate(exam_period_dates)}
        exam_period_str_range = '%s - %s' % (exam_period_start.strftime('%m/%d/%Y'), exam_period_end.strftime('%m/%d/%Y'))

        ws = wb.add_sheet('Reading Period Sheet', cell_overwrite_ok=True)
        ws.write(0,0, u'Courses with assignment due dates during Reading Period: {reading_period}'.format(reading_period=reading_period_str_range).encode('utf-8'), bold_style)
        ws.write(1,0, u'Term'.encode('utf-8'), bold_style)
        ws.write(1,1, u'Course'.encode('utf-8'), bold_style)
        ws.write(1,2, u'Due Dates during Reading Period?'.encode('utf-8'), bold_style)
        ws.write(1,3, u'Due Dates also during Exam Period?'.encode('utf-8'), bold_style)
        for (period_dates, period_date_col) in [(reading_period_dates,reading_period_date_col), (exam_period_dates,exam_period_date_col)]:
            for d in period_dates:
                ws.write(1, period_date_col[d.strftime('%Y-%m-%d')], d.strftime('%a %b %d, %Y'), bold_style)

        row = 2
        for course in courses:
            course_id = str(course['id'])
            course_assignments = assignments[course_id]
            has_reading_period_due_date = False
            has_exam_period_due_date = False
            reading_dates = []
            exam_dates = []
            for assignment in course_assignments:
                due_at = assignment['due_at']
                if due_at:
                    due_date = dateutil.parser.parse(due_at).replace(tzinfo=UTC_TZ).astimezone(EST_TZ)
                    if (due_date >= reading_period_start and due_date <= reading_period_end):
                        has_reading_period_due_date = True
                        reading_dates.append(due_date)
                    elif (due_date >= exam_period_start and due_date <= exam_period_end):
                        has_exam_period_due_date = True
                        exam_dates.append(due_date)
            if has_reading_period_due_date:
                ws.write(row, 0, course['term']['name'])
                ws.write(row, 1, course_name_fmt.format(**course))
                ws.write(row, 2, 'YES')
                ws.write(row, 3, 'YES' if has_exam_period_due_date else 'NO')
                for d in reading_dates:
                    ws.write(row, reading_period_date_col[d.strftime('%Y-%m-%d')], 'X')
                for d in exam_dates:
                    ws.write(row, exam_period_date_col[d.strftime('%Y-%m-%d')], 'X')
                row += 1

    # Worksheet 2
    ws = wb.add_sheet('Courses Sheet', cell_overwrite_ok=True)
    ws.write(0,0, u'All course assignment due dates'.encode('utf-8'), bold_style)
    ws.write(1,0, u'Term'.encode('utf-8'), bold_style)
    ws.write(1,1, u'Course'.encode('utf-8'), bold_style)
    ws.write(1,2, u'Assignment'.encode('utf-8'), bold_style)
    ws.write(1,3, u'Due Date (UTC)'.encode('utf-8'), bold_style)
    ws.write(1,4, u'Due Date (EST)'.encode('utf-8'), bold_style)
    
    # Write data to worksheet
    row = 2
    for course_idx, course in enumerate(courses):
        course_id = str(course['id'])
        course_assignments = assignments[course_id]
        for assignment_idx, assignment in enumerate(course_assignments):
            ws.write(row, 0, course['term']['name'])
            ws.write(row, 1, course_name_fmt.format(**course))
            ws.write(row, 2, assignment_name_fmt.format(**assignment))
            ws.write(row, 3, due_at_fmt.format(**assignment))
            due_date = assignment['due_at']
            if due_date:
                due_date = dateutil.parser.parse(due_date).astimezone(EST_TZ).strftime('%a, %b %d at %I:%M%p')
            else:
                due_date = 'None'
            ws.write(row, 4, due_date)
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
#print_statistics(data)
save_spreadsheet(filename='duedates.xls', data=data)
exit(0)
