# Canvas Page Views Utility

This script can be used to generate the total number of page views for a course over a specific time range. This tool exists because Canvas doesn't provide this functionality out of the box. It only provides an interface to view an individual user's page views, so this tool fills the gap until Canvas adds that functionality. 

**Requirements:**
This script requires the "Requests" library. In order to install this library, use pip:

```sh
$ pip install requests
```

In order to use this library, it is highly recommended that you upgrade to at least Python 2.7.9. Otherwise, you might see the following error/warning when you run the script:

```
InsecurePlatformWarning: A true SSLContext object is not available. This prevents urllib3 from configuring SSL appropriately and may cause certain SSL connections to fail. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning.
```

Check the link in the error for more information.

**Usage:**

```sh
$ echo "my-oauth-token" > oauthtoken.txt
$ ./canvas_page_views.py --help
$ ./canvas_page_views.py 1693 --start_time 2015-01-26 --end_time 2015-03-12 --enrollment_types StudentEnrollment >log.txt 2>&1
$ open pageviews_1693_2015-01-26-2015-03-12.csv -a /Applications/Microsoft\ Office\ 2011/Microsoft\ Excel.app/
$ cat pageviews_1693_2015-01-26-2015-03-12.json
```

1. Creates *oauthtoken.txt* and adds your OAuth access token to it. Note: if you don't already have an OAuth access token, you can generate one from your [profile settings](https://canvas.harvard.edu/profile/settings). Just click the *New Access Token* button at the bottom of the page and follow the directions to generate the token, and then copy and paste it into the ```oauthtoken.txt``` file.
2. Prints the help/usage info for the *canvas_page_views.py* script.
3. Runs the *canvas_page_views.py* script to generate page views for course 1693 between the date range Jan 26th - March 12th of 2015, filtering the page views so that only student enrollments are counted, and finally, redirects the output to a log file.
4. Opens the resulting CSV file with the page view data in Microsoft Excel.
5. Prints the JSON file to the console for inspection. 

**Output:**

The script generates 3 reports with  page view results, and each report is available in CSV and JSON. The three reports are:

1. Total page views (URL, Count).
2. Total page views by user (User, URL, Count).
3. User page view records (User, URL, Request Date).

The third report is the most granular, since it gives you each page view record for each user in the course. This report is then rolled up to the user (report #2), and the course overall (report #1). All three reports are generated at the same time.

**Caveats:**

This script reports **page views**, which Canvas considers distinct from **asset accessess**. The latter is what you will find on the "Access Report" page for a user:

https://canvas.harvard.edu/courses/:course_id/users/:user_id/usage

See the [application controller comments](https://github.com/instructure/canvas-lms/blob/01dd6697795b0f4ae734bd2538e7e58fec63ab7e/app/controllers/application_controller.rb#L853) on the [canvas-lms](://github.com/instructure/canvas-lms) github account.

There is some logic in there so that page views are not double-counted, which accounts for the discrepancy with "Times Viewed" on the "Access Report," which is equal to or greater than the page view count.

**Canvas Resources:**

1. Basic Canvas API Documentation: https://canvas.instructure.com/doc/api/index.html
2. Pagination: https://canvas.instructure.com/doc/api/file.pagination.html
2. Getting enrollments: https://canvas.instructure.com/doc/api/enrollments.html
3. List a user's page views: https://canvas.instructure.com/doc/api/users.html#method.page_views.index
4. Pages API: https://canvas.instructure.com/doc/api/pages.html
