# README

This is a skeleton directory intended to be cloned.

### Quickstart ###

```sh
$ touch settings/secure.py
$ echo "OAUTH_TOKEN=''" >> settings/secure.py
$ echo "CANVAS_URL=''" >> settings/secure.py
```

Update ```settings/secure.py``` with the appropriate values.

```sh
$ python skeleton.py
```

If it works as expected, you should see a list of your courses printed to the console in JSON format.
