from collections import defaultdict
from flask import Flask, jsonify, request
import logging
from logging.config import fileConfig
from configparser import ConfigParser
import os
import sys
import csv
from flask_compress import Compress
from waitress import serve
import re
import yaml
from pprint import pprint


app = Flask(__name__)
Compress(app)


def readConfig(configFile):
    try:
        if os.path.exists(os.path.join('./', configFile)):
            parserData = ConfigParser()
            parserData.read(os.path.join('./', configFile))
            return parserData
        else:
            logger.error('Config file {} not found. Ensure that it exists in the same directory'.format(configFile))
    except Exception as e:
        logger.error('Error occurred while trying to read the config file.'.format(str(e)))


def read_config(config_path, config_file):
    try:
        if os.path.exists(os.path.join(config_path, config_file)):
            parserData = yaml.safe_load(open(os.path.join(config_path, config_file)))
            return parserData
        else:
            logger.error('Config file {} not found. Ensure that it exists in the same directory'.format(config_file))
            exit(1)
    except:
        logger.error('Config file {} could not be loaded. Ensure that it exists in the same directory'.format(config_file))
        exit(1)

def set_in_dict(d, keys, value):
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value

def merge_env_variables(config, prefix='APP__'):
    for name,val in os.environ.items():
        if name.startswith(prefix):
            key_path = name[len(prefix):].lower().split('__')
            if val.lower() in ("true", "false", "null"):
                parsed = {"true": True, "false": False, "null": None}[val.lower()]
            else:
                try:
                    parsed = int(val)
                except:
                    try:
                        parsed = float(val)
                    except:
                        parsed = val
            set_in_dict(config, key_path, parsed)
    return config


def configureLogging(logging_path, configFile):
    try:
        if os.path.exists(os.path.join(logging_path, configFile)):
            fileConfig(os.path.join(logging_path, configFile), disable_existing_loggers=True)
            loggerObj = logging.getLogger()
            return loggerObj
        else:
            print('Logging Config not found.')
            sys.exit(1)
    except Exception as e:
        print('Error occurred while trying to read logging config. {}'.format(str(e)))
        sys.exit(1)


@app.route('/<csvFile>')
def getData(csvFile):
    if csvFile in config.keys():
        section = csvFile
        logger.debug('Explicit config section found for {}'.format(csvFile))
    else:
        section = 'global'
        logger.debug('No section found for {}. Using Global config'.format(csvFile))
    if os.path.exists(os.path.join(config[section].get('csv_path'), csvFile + '.csv')):
        logger.debug('CSV file found in the path.')
        headers = []
        jsonData = []
        with open(os.path.join(config[section].get('csv_path'), csvFile + '.csv'), 'r') as infile:
            csvData = csv.reader(infile)
            for index, line in enumerate(csvData):
                if index == 0:
                    if 'headers' in config[section].keys():
                        logger.debug('Headers found in configuration to be used as JSON keys. Ignoring the first line and using this instead.')
                        headers = config[section].get('headers').split(',')
                    else:
                        logger.debug('Using the first line as headers')
                        headers = line
                else:
                    jsonData.append({str(headers[index].replace('"', '').strip()): str(column.replace('"', '').strip()) for index, column in enumerate(line)})
        return jsonify(jsonData), 200
    else:
        logger.error('File Not found in path.')
        return {'error': 'File not found'}, 404


@app.route('/<csvFile>/search')
def searchData(csvFile):
    if len(list(request.args.keys())) >= 1:
        paramName = []
        paramValue = []
        for params in request.args.keys():
            paramName.append(params.lower())
            paramValue.append(request.args.get(params).lower())
        if csvFile in config.keys():
            section = csvFile
            logger.debug('Explicit config section found for {}'.format(csvFile))
        else:
            section = 'Global'
            logger.debug('No section found for {}. Using Global config'.format(csvFile))
        if os.path.exists(os.path.join(config[section].get('csv_path'), csvFile + '.csv')):
            logger.debug('CSV file found in the path.')
            headers = []
            jsonData = defaultdict(list)
            with open(os.path.join(config[section].get('csv_path'), csvFile + '.csv'), 'r') as infile:
                csvData = csv.reader(infile)
                for index, line in enumerate(csvData):
                    if index == 0:
                        if 'headers' in config[section].keys():
                            logger.debug('Headers found in configuration to be used as JSON keys. Ignoring the first line and using this instead.')
                            headers = config[section]['headers'].split(',')
                        else:
                            logger.debug('Using the first line as headers')
                            headers = line
                    else:
                        status = 0
                        for lineIndex, column in enumerate(line):
                            if headers[lineIndex].replace('"', '').strip().lower() in paramName:
                                if column.replace('"', '').strip().lower() in paramValue[paramName.index(headers[lineIndex].replace('"', '').lower().strip())] or re.search(paramValue[paramName.index(headers[lineIndex].replace('"', '').strip().lower())], column, re.IGNORECASE):
                                    status += 1
                        if status == len(paramName):
                            jsonData['result'].append({str(headers[index].replace('"', '').strip()): str(column.replace('"', '').strip()) for index, column in enumerate(line)})
            jsonData['count'] = len(jsonData['result'])
            return jsonify(jsonData), 200
        else:
            logger.error('File Not found in path.')
            return {'error': 'File not found'}, 404
    else:
        logger.error('Did not find any search parameters')
        return {'error': 'No search parameter defined with search endpoint.'}, 500


if __name__ == '__main__':
    if 'APP_LOGGING_PATH' in os.environ.keys():
        logging_path = os.environ['APP_LOGGING_PATH']
    else:
        logging_path = './'

    logger = configureLogging(logging_path,'logging_config.ini')
    #parser = readConfig('init.conf')
    if 'APP_CONFIG_PATH' in os.environ.keys():
        config_path = os.environ['APP_CONFIG_PATH']
    else:
        config_path = './'
    config = read_config(config_path,'init.yml')
    config = merge_env_variables(config)
    pprint(config)
    app.secret_key = os.urandom(16)
    # app.run(debug=True, port=5555, host='0.0.0.0')
    # app.debug = True
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    serve(app, port=int(config.get('global').get('port')), host='0.0.0.0', url_scheme='https')
