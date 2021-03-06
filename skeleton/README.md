# README

This is a skeleton directory intended to be cloned. You will need to be familiar with the canvas API docs and Canvas Python SDK:

1. [API DOCS](https://canvas.instructure.com/doc/api/index.html)
2. [Canvas SDK](https://github.com/penzance/canvas_python_sdk) (Note: the [wiki](https://github.com/penzance/canvas_python_sdk/wiki) has some background info about how to use the SDK)

Use the [methods](https://github.com/penzance/canvas_python_sdk/tree/master/canvas_sdk/methods) to interact with the [API endpoints](https://canvas.instructure.com/doc/api/all_resources.html). The ```skeleton.py``` contains an example to get you started.

### Quickstart ###

```sh
$ cp settings/secure.py.example settings/secure.py
```

Open ```settings/secure.py``` in your favorite text editor and update with the appropriate values.

```sh
$ python skeleton.py
```

If it works as expected, you should see a list of your courses printed to the console in JSON format.

