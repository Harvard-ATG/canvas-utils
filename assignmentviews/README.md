# README

This script is used to get page view statistics of assignments in a given course.

### Quickstart ###

Make sure you've initialized your python virtualenv and installed the requirements (see canvas-utils  [README](https://github.com/Harvard-ATG/canvas-utils/blob/master/README.md)).

```sh
$ cp settings/secure.py.example settings/secure.py
```

Update ```settings/secure.py``` with the appropriate values for *OAUTH_TOKEN*, *CANVAS_URL*, and *TEST_CANVAS_URL*.

```sh
$ python assignmentviews.py [course_id] --anonymize_students_csv [csv_filename]
```

### NOTES ###

- In order to get student enrollment, you must unconclude the course in the TEST environment and then query the TEST canvas API.
- In order get page views for the students in the course, you must query the PROD canvas API, not the TEST canvas API. 
- It's an open question as to *why* we can't get page views in the TEST environment. Maybe because they aren't synced over from PROD along with the rest of the course data?
