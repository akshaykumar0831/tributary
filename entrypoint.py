# import statements
import json
import redis as redis
from flask import Flask, request
from loguru import logger

HISTORY_LENGTH = 10
DATA_KEY = "engine_temperature"

# create a Flask server, and allow us to interact with it using the app variable
app = Flask(__name__)
app.run(debug=True)


# define an endpoint which accepts POST requests, and is reachable from the /record endpoint
@app.route('/record', methods=['POST'])
def record_engine_temperature():
    # every time the /record endpoint is called, the code in this block is executed
    payload = request.get_json(force=True)
    logger.info(f"(*) record request --- {json.dumps(payload)} (*)")

    engine_temperature = payload.get("engine_temperature")
    logger.info(f"engine temperature to record is: {engine_temperature}")

    # open up a connection to the redis database
    database = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    database.lpush(DATA_KEY, engine_temperature)
    logger.info(f"stashed engine temperature in redis: {engine_temperature}")

    # discard the old engine temperature readings as new ones appear
    while database.llen(DATA_KEY) > HISTORY_LENGTH:
        database.rpop(DATA_KEY)
    engine_temperature_values = database.lrange(DATA_KEY, 0, -1)
    logger.info(f"engine temperature list now contains these values: {engine_temperature_values}")

    logger.info(f"record request successful")

    # return a json payload, and a 200 status code to the client
    return {"success": True}, 200


# define an endpoint which accepts POST requests, and is reachable from the /collect endpoint
@app.route('/collect', methods=['POST'])
def collect_engine_temperature():
    # open up a connection to the redis database
    database = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)

    # retrieve all stored engine temperature readings
    engine_temperature_values = database.lrange(DATA_KEY, 0, -1)
    logger.info(f"engine temperature list is now retrieved from redis: {engine_temperature_values}")

    if not engine_temperature_values:
        # case where there are no values in the database
        logger.warning("No engine temperature data available in the redis database.")
        return {
                   "current_engine_temperature": None,
                   "average_engine_temperature": None,
                   "message": "No data available"
               }, 200

    # get the most recent temperature value
    current_engine_temperature = float(engine_temperature_values[0])
    logger.info(f"current engine temperature: {current_engine_temperature}")

    # get the mean engine temperature value
    average_engine_temperature = sum(map(float, engine_temperature_values)) / len(engine_temperature_values)
    logger.info(f"average engine temperature: {average_engine_temperature}")

    # return the response as a dictionary
    return {
               "current_engine_temperature": current_engine_temperature,
               "average_engine_temperature": average_engine_temperature
           }, 200
