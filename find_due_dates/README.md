# README

Find due dates for all assignments in the Spring 2015-2016 term and then show any courses that have due dates set during reading period (Th. April 28th to Wed. May 4th):

```sh
$ python find_due_dates.py 39 --enrollment_term_id 39 --reading_period_start 2016-04-28 --reading_period_end 2016-05-04 --exam_period_start 2016-05-05 --exam_period_end 2016-05-14
```

### Setup your environment

If you don't already have your environment setup to run these canvas util scripts, here's an overview of what you need to do:

```sh
$ git clone https://github.com/Harvard-ATG/canvas-utils.git
$ cd canvas-utils/
$ virtualenv pyenv
$ source pyenv/bin/activate
$ pip install -r requirements.txt
$ cd find_due_dates/
$ cp settings/secure.py.example settings/secure.py
```

After the last step, you should open up `settings/secure.py` and update the values as appropriate. Then you should be ready to run the script:

```sh
$ python find_due_dates.py 
usage: find_due_dates.py [-h] [--enrollment_term_id ENROLLMENT_TERM_ID]
                         [--reading_period_start READING_PERIOD_START]
                         [--reading_period_end READING_PERIOD_END]
                         [--exam_period_start EXAM_PERIOD_START]
                         [--exam_period_end EXAM_PERIOD_END]
                         account_id
find_due_dates.py: error: too few arguments
```
