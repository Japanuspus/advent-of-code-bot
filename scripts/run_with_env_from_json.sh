$( jq -r 'keys[] as $k | "export \($k)=\(.[$k])"' env.test.json )
python functions/advent_of_code_bot/lambda_function.py $*

