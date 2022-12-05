#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

if [ $# -lt 1 ]; then
  echo 1>&2 "$0: not enough arguments. Usage: $0 env_file"
  exit 2
fi

function_name=advent_of_code_bot

vars=$(jq -c '{"Variables": .}' "$1") 
aws lambda update-function-configuration --no-cli-pager --function-name $function_name --environment "$vars"
aws lambda wait function-updated --no-cli-pager --function-name $function_name

(cd functions/advent_of_code_bot && zip lambda.zip lambda_function.py)
aws lambda update-function-code --no-cli-pager --function-name $function_name --zip-file fileb://functions/advent_of_code_bot/lambda.zip
aws lambda wait function-updated --no-cli-pager --function-name $function_name
