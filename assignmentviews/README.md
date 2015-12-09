# README

This script is used to get page view statistics of assignments in a given course.

### Quickstart ###

Make sure you've initialized your python virtualenv and installed the requirements (see canvas-utils  [README](https://github.com/Harvard-ATG/canvas-utils/blob/master/README.md)).

```sh
$ cp settings/secure.py.example settings/secure.py
```

Update ```settings/secure.py``` with the appropriate values for *OAUTH_TOKEN*, *CANVAS_URL*, and *TEST_CANVAS_URL*.

```sh
$ python assignmentviews.py [course_id]
```

To anonymize the students by assigning random IDs to their HUIDs, create a CSV file with the following columns: ```RandomID,FirstName,LastName,HUID``` and then run the script like this: 

```
$ python assignmentviews.py [course_id] --anonymize_students_csv [csv_filename]
```

To limit the scope of the page views to a particular date range, use the *start_time* and *end_time* options:

```
$ python assignmentviews.py [course_id] --start_time 2015-01-01 --end_time 2015-06-01
```

### USAGE ##

```sh
$ python assignmentviews.py --help
usage: assignmentviews.py [-h]
                          [--anonymized_students_csv ANONYMIZED_STUDENTS_CSV]
                          [--start_time START_TIME] [--end_time END_TIME]
                          course_id

Gets assignment and submission data with rubric assessments for a given
course.

positional arguments:
  course_id             The canvas course ID

optional arguments:
  -h, --help            show this help message and exit
  --anonymized_students_csv ANONYMIZED_STUDENTS_CSV
                        CSV file that maps student HUID's to random
                        identifiers to anonymize the data
  --start_time START_TIME
                        Start time ISO 8601 format YYYY-MM-DD.
  --end_time END_TIME   End time ISO 8601 format YYYY-MM-DD.
```

### NOTES ###

- In order to get student enrollment, you must unconclude the course in the TEST environment and then query the TEST canvas API.
- In order get page views for the students in the course, you must query the PROD canvas API, not the TEST canvas API. 
- It's an open question as to *why* we can't get page views in the TEST environment. Maybe because they aren't synced over from PROD along with the rest of the course data?
