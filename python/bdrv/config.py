import os
from dotenv import load_dotenv

load_dotenv()
SURVEY_TIME = os.getenv('SURVEY_TIME')
BEACON_TIME = os.getenv('BEACON_TIME')
CONFIG_SENSOR = os.getenv('CONFIG_SENSOR')
ERROR_MESSAGE_LOG = os.getenv('ERROR_MESSAGE_LOG')