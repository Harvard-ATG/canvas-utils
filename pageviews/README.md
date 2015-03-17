# Canvas Page Views Utility

This script can be used to generate the total number of page views for a course over a specific time range. This tool exists because Canvas doesn't provide this functionality out of the box. It only provides an interface to view an individual user's page views, so this tool fills the gap until Canvas adds that functionality. 

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

The output of this script is a CSV and JSON file with the aggregated page views for each URL that enrolled users in the course have visited. The CSV file contains four columns: ```URL, Page Views, Start Time, End Time```. The JSON file is an array of page view objects:

```javascript
[
    {  
        "url": "https://canvas.harvard.edu/"
        "pageviews": 1,
        "end_time": "2015-03-16",
        "start_time": "2015-01-26"
    }
]
```

