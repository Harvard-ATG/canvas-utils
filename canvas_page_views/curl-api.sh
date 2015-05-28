#!/bin/bash
#
# Script to run quick tests against the API using curl.
#
# Usage:
# 
# ./curl-api.sh courses
# ./curl-api.sh users/27/page_views start_time=2015-05-01&end_time=2015-05-28
#

if [ ! -e "./oauthtoken.txt" ]; then
	echo "You must setup oauthtoken.txt to make API requests."
	exit;
fi

ENDPOINT=$1
QUERY_PARAMS=$2
OAUTH_TOKEN=$(cat oauthtoken.txt)

if [ -z "$ENDPOINT" ]; then
	ENDPOINT="courses"
fi

API_URL="https://canvas.harvard.edu/api/v1/$ENDPOINT"
if [ ! -z "$QUERY_PARAMS"]; then
	API_URL="$API_URL?$QUERY_PARAMS"
fi

AUTH_HEADER="Authorization: Bearer $OAUTH_TOKEN"
echo "AUTH_HEADER=$AUTH_HEADER API_URL=$API_URL"

RESPONSE=$(curl "$API_URL" -H "$AUTH_HEADER" | python -mjson.tool)
echo "RESPONSE=$RESPONSE"
