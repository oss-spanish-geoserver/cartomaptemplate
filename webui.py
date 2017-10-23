#!/usr/bin/env python
import ConfigParser
import os
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_wtf.csrf import CsrfProtect
from flask import Flask, send_file, render_template
from werkzeug.utils import secure_filename
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
# from dotcarto import DotCartoFile

from flask import render_template, request, redirect, url_for, jsonify, flash
# from app import app
import json
# import requests
from cartodb import CartoDBAPIKey, CartoDBException, FileImport
from datetime import datetime


class Config(object):
    """
    Looks for config options in a config file or as an environment variable
    """
    def __init__(self, config_file_name):
        self.config_parser = ConfigParser.RawConfigParser()
        self.config_parser.read(config_file_name)

    def get(self, section, option):
        """
        Tries to find an option in a section inside the config file. If it's not found or if there is no
        config file at all, it'll try to get the value from an enviroment variable built from the section
        and options name, by joining the uppercase versions of the names with an underscore. So, if the section is
        "platform" and the option is "secret_key", the environment variable to look up will be PLATFORM_SECRET_KEY
        :param section: Section name
        :param option: Optionname
        :return: Configuration value
        """
        try:
            return self.config_parser.get(section, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return os.environ.get("%s_%s" % (section.upper(), option.upper()), None)


config = Config("dotcarto.conf")

app = Flask(__name__)
if config.get("webui", "debug"):
    app.debug = True
app.secret_key = config.get("webui", "secret_key")
CsrfProtect(app)


def openJSON(inFile):
    with open(inFile) as json_data:
        data = json.load(json_data)
    return data


def saveJSON(data, ouFile):
    with open(ouFile, 'w') as outfile:
        json.dump(data, outfile)


def replaceDataset(data, oldTableName, newTableName):
    print 'running replaceDataset'
    data = json.loads(json.dumps(data).replace(oldTableName, newTableName))
    return data


def openFileReplaceDatasetSave(inFile, ouFile, oldTableName, newTableName):
    print 'running openFileReplaceDatasetSave'
    data = replaceDataset(openJSON(inFile), oldTableName, newTableName)
    saveJSON(data, ouFile)
    return data


class DotCartoForm(FlaskForm):
    filenames = ['DMA Heatmap', 'Location Visit Index']  # old ['DMA Heatmap', 'DMA Heatmap 2', 'Location Visit Index']  # This will be generated by you
    carto_api_endpoint = StringField("CARTO Username", validators=[DataRequired()], description="Your CARTO username.")
    carto_api_key = StringField("CARTO API key", validators=[DataRequired()], description='Found on the "Your API keys" section of your user profile.')
    # original_dotcarto_file = FileField("Original .carto file", validators=[FileAllowed(["carto"], ".carto files only!")],
    #                                    description=".carto file where datasets will be swapped")
    cartojsontemplate = SelectField("Map template name", validators=[DataRequired()], choices=[(f, f) for f in filenames], description="The map template to generate a new map.")
    new_dataset_names = StringField("New dataset names", validators=[DataRequired()], description="dma_test or visitindex_test")
    map_title_name = StringField("Map title name", validators=[DataRequired()], description='Name the map, for example "DMA Regions April".')


@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    form = DotCartoForm()
    fi = None
    first = None
    old_map_name = None

    if form.validate_on_submit():
        # import ipdb; ipdb.set_trace()
        # cred = json.load(open('credentials.json')) # modify credentials.json.sample
        # if username == '':
        username = form.carto_api_endpoint.data
        # if apikey == '':
        apikey = form.carto_api_key.data
        # if cartojson == '':
        cartojson = form.cartojsontemplate.data.replace(' ', '_').lower()+'.carto.json'
        # if first == '':
        print 'cartjson assigned'
        # if cartojson == 'dma_heatmap.carto.json':
        #     first = 'dma_master_polygons_merge'
        if cartojson == 'dmas-oct.carto.json':
            first = 'dma_visit_index_template_data_may2017v1'
        elif cartojson == 'visits-final.carto.json':
            first = 'visitindexheatmapexample'
        print first
        # if second == '':
        second = form.new_dataset_names.data
        # if cartojson == 'dma_heatmap.carto.json':
        #     old_map_name = "TEMPLATE (USE THIS) - DMA Heatmap"
        if cartojson == 'dmas-oct.carto.json':
            old_map_name = "FINAL - DMA Heatmap"
        elif cartojson == 'visits-final.carto.json':
            old_map_name = "TEMPLATE (USE THIS) - Location Visit Index"

        print first
        new_map_name = form.map_title_name.data

        # cartojson = 'template.carto.json'
        curTime = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        inFile = 'data/'+cartojson
        ouFile = 'data/_temp/'+cartojson.replace('.carto.json', '')+'_'+curTime+'.carto.json'
        fiFile = 'data/_temp/'+new_map_name.replace(' ', '_').lower()+'_'+cartojson.replace('.carto.json', '')+'_'+curTime+'.carto.json'
        print inFile, ouFile, first, second
        openFileReplaceDatasetSave(inFile, ouFile, first, second)
        print inFile, ouFile, old_map_name, new_map_name
        openFileReplaceDatasetSave(ouFile, fiFile, old_map_name, new_map_name)

        cl = CartoDBAPIKey(apikey, username)

        # Import csv file, set privacy as 'link' and create a default viz
        fi = FileImport(fiFile, cl, create_vis='true', privacy='link')
        fi.run()
    return render_template("index.html", form=form, result=[str(fi)])


if __name__ == "__main__":
    app.run()
