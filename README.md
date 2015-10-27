# canvas-utils

A collection of utilities and scripts for working with the Canvas LMS.

## Quickstart

Initialize your python virtual environment and install python module requirements:

```sh
$ virtualenv pyenv
$ source pyenv/bin/activate
$ pip install -r requirements.txt
```

### Skeleton ###

To start a new python script to interact with the Canvas API, use the [skeleton](https://github.com/Harvard-ATG/canvas-utils/tree/master/skeleton).

### cURL Utility ###

To run a quick test against the API using cURL:

```sh
env CANVAS_URl='https://canvas/api' OAUTH_TOKEN='mytoken' ./curl-api.sh courses
```

The above example hits the [list your courses](https://canvas.instructure.com/doc/api/all_resources.html#method.courses.index) endpoint.
