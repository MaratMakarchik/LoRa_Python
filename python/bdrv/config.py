import os
from dotenv import load_dotenv

load_dotenv()
SURVEY_TIME = int(os.getenv('SURVEY_TIME'))
BEACON_TIME = int(os.getenv('BEACON_TIME'))
CONFIG_SENSOR = os.getenv('CONFIG_SENSOR')
ERROR_MESSAGE_LOG = os.getenv('ERROR_MESSAGE_LOG')