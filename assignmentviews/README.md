# README

This script is used to get page view statistics of assignments in a given course.

### Quickstart ###

Make sure you've initialized your python virtualenv and installed the requirements (see canvas-utils  [README](https://github.com/Harvard-ATG/canvas-utils/blob/master/README.md)).

```sh
$ cp settings/secure.py.example settings/secure.py
```

Update ```settings/secure.py``` with the appropriate values for *OAUTH_TOKEN* and *CANVAS_URL*.

```sh
$ python assignmentviews.py [course_id]
```

