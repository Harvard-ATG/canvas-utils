#!/bin/bash
#
# Script to run quick tests against the API using curl.
#
# Usage:
# 
#     export OAUTH_TOKEN='mytoken'
#     export CANVAS_URL='https://canvas.localhost/api'
#     ./curl-api.sh courses
#
#     -- OR --
# 
#    env CANVAS_URL='https://canvas.localhost/api' OAUTH_TOKEN='mytoken' ./curl-api.sh courses
#    env CANVAS_URL='https://canvas.localhost/api' OAUTH_TOKEN='mytoken' ./curl-api.sh users/123/page_views start_time=2015-05-01&end_time=2015-05-28
#

ENDPOINT=$1
QUERY_PARAMS=$2

if [ -z "$ENDPOINT" ]; then
	ENDPOINT="courses"
fi

API_URL="$CANVAS_URL/v1/$ENDPOINT" 
if [ ! -z "$QUERY_PARAMS" ]; then
	API_URL="$API_URL?$QUERY_PARAMS"
fi

AUTH_HEADER="Authorization: Bearer $OAUTH_TOKEN"
>&2 echo "AUTH_HEADER=$AUTH_HEADER API_URL=$API_URL"

RESPONSE=$(curl --silent "$API_URL" -H "$AUTH_HEADER" | python -mjson.tool)
echo "$RESPONSE"
