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


def configureLogging(configFile):
    try:
        if os.path.exists(os.path.join('./', configFile)):
            fileConfig(os.path.join('./', configFile), disable_existing_loggers=True)
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
    if parser.has_section(csvFile):
        section = csvFile
        logger.debug('Explicit config section found for {}'.format(csvFile))
    else:
        section = 'Global'
        logger.debug('No section found for {}. Using Global config'.format(csvFile))
    if os.path.exists(os.path.join(parser.get(section, 'csv_path'), csvFile + '.csv')):
        logger.debug('CSV file found in the path.')
        headers = []
        jsonData = []
        with open(os.path.join(parser.get(section, 'csv_path'), csvFile + '.csv'), 'r') as infile:
            csvData = csv.reader(infile)
            for index, line in enumerate(csvData):
                if index == 0:
                    if parser.has_option(section, 'headers'):
                        logger.debug('Headers found in configuration to be used as JSON keys. Ignoring the first line and using this instead.')
                        headers = parser.get(section, 'headers').split(',')
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
        if parser.has_section(csvFile):
            section = csvFile
            logger.debug('Explicit config section found for {}'.format(csvFile))
        else:
            section = 'Global'
            logger.debug('No section found for {}. Using Global config'.format(csvFile))
        if os.path.exists(os.path.join(parser.get(section, 'csv_path'), csvFile + '.csv')):
            logger.debug('CSV file found in the path.')
            headers = []
            jsonData = defaultdict(list)
            with open(os.path.join(parser.get(section, 'csv_path'), csvFile + '.csv'), 'r') as infile:
                csvData = csv.reader(infile)
                for index, line in enumerate(csvData):
                    if index == 0:
                        if parser.has_option(section, 'headers'):
                            logger.debug('Headers found in configuration to be used as JSON keys. Ignoring the first line and using this instead.')
                            headers = parser.get(section, 'headers').split(',')
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
    logger = configureLogging('logging_config.ini')
    parser = readConfig('init.conf')
    app.secret_key = os.urandom(16)
    # app.run(debug=True, port=5555, host='0.0.0.0')
    # app.debug = True
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    serve(app, port=parser.get('Global', 'Port'), host='0.0.0.0', url_scheme='https')
