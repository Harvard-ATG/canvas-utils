# README

This script is used to get rubric assessment data for all of the assignments in a given course.

### Quickstart ###

```sh
$ cp settings/secure.py.example settings/secure.py
```

Update ```settings/secure.py``` with the appropriate values for *OAUTH_TOKEN* and *CANVAS_URL*.

```sh
$ python rubricassessments.py [course_id]
$ open [course_id].xls
```

If it worked, you should see  log output while the python script executed and then three files should have been created in the current directory. For example, assuming ```course_id=123```, you should see these files:

* _123.json_: contains the raw data fetched from the Canvas API.
* _123-transformed.json_: contains the transformed data used to generate the spreadsheet.
* _123.xls_: the Excel spreadsheet that contains students and their associated rubric assessments for each assignment that had a rubric.
