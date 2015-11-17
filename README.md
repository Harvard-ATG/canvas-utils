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

Use the [skeleton](https://github.com/Harvard-ATG/canvas-utils/tree/master/skeleton) as a template to get started with a new utility script:

```sh
$ cp -r skeleton myscript
$ touch myscript/settings/secure.py
$ cd myscript/
```

### cURL Utility ###

To run a quick-and-dirty test against the API using cURL:

```sh
env CANVAS_URl='https://canvas/api' OAUTH_TOKEN='mytoken' ./curl-api.sh courses
```

The above example hits the [list your courses](https://canvas.instructure.com/doc/api/all_resources.html#method.courses.index) endpoint.
