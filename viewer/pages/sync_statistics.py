#!/usr/bin/env python3
# -*- coding: utf-8 -*

import os
import sys
sys.path.append( os.path.dirname(os.path.dirname(os.path.abspath(__file__)) ) )

from scripts.src.func import *

from configs.development import *


PAGE_NAME = "sync_statistics"

sync_statistics_api = Blueprint('sync_statistics_api', __name__)

@sync_statistics_api.route("/sync_statistics", methods=['GET', 'POST'])
def sync_statistics():
    args = getArgs()

    def __connectMongoDB(host, port, username, keypath):
        # Development environment
        if args.is_development:
            url = "mongodb://%s:%d" % (host, port)
            logging.info("server url is: %s" % (url) )
            return MongoClient(url)["localdbtools"]

        # Production environment
        if username and keypath:
            if os.path.exists(keypath):
                key_file = open(keypath, "r")
                key = key_file.read()
            else:
                logging.error("API Key not exist!")
                exit(1)
        else:
            logging.error("user name or API Key not given!")
            exit(1)
        url = "mongodb://%s:%s@%s:%d" % (username, key, host, port)
        logging.info("server url is: %s" % (url) )
        return MongoClient(url)["localdbtools"]

    def __getCommitRelationship(commit_doc, layer_count, marker_x, marker_y, line_x, line_y):
        while True:
            #==========================
            # parent --- child
            #==========================
            # child
            marker_x.append(commit_doc["sys"]["cts"])
            marker_y.append(layer_count)

            # line between parent and child
            if commit_doc["parent"] == "" or commit_doc["parent"] == "no_parent_commit_id": break
            line_x.append(commit_doc["sys"]["cts"])
            line_y.append(layer_count)
            parent_commit_doc = localdbtools_db["commits"].find_one({"_id": commit_doc["parent"]})
            line_x.append(parent_commit_doc["sys"]["cts"])
            line_y.append(layer_count)

            #==========================
            # parent ---------- child
            #                |
            # parent_merge ---
            #==========================
            if commit_doc["commit_type"] == "merge" and commit_doc["parent_merge"] != "":
                # line between parent_merge and child
                line_x.append(commit_doc["sys"]["cts"])
                line_y.append(layer_count)
                parent_master_commit_doc = localdbtools_db["commits"].find_one({"_id": commit_doc["parent_merge"]})
                line_x.append(parent_master_commit_doc["sys"]["cts"])
                line_y.append(layer_count+1)
                #merge_count += 1
                __getCommitRelationship(parent_master_commit_doc, layer_count+1, marker_x, marker_y, line_x, line_y)

            # Go to parent commit
            #commit_count += 1
            commit_doc = parent_commit_doc

    # Connect to DB localdbtools
    localdbtools_db = __connectMongoDB(args.host, args.port, args.username, args.password)

    # Get head reference
    master_head_ref_doc = localdbtools_db["refs"].find_one({"ref_type": "head"})
    if not master_head_ref_doc:
        return render_template("sync_statistics.html")

    # Get last commit
    last_commit_doc = localdbtools_db["commits"].find_one({"_id": master_head_ref_doc["last_commit_id"]})
    if not last_commit_doc:
        return render_template("sync_statistics.html")

    marker_x = [] # commit_datetimes
    marker_y = [] # commit_layer
    line_x = []
    line_y = []
    commit_description = [] # text
    #commit_count = 0
    #merge_count = 0
    layer_count = 0
    __getCommitRelationship(last_commit_doc, layer_count, marker_x, marker_y, line_x, line_y)

    #print(marker_x)
    #print(marker_y)
    #print(line_x)
    #print(line_y)

    graph = dict(
            data = [
                    dict(
                            x = marker_x,
                            y = marker_y,
                            text = commit_description,
                            type ="scatter",
                            name = "hoge",
                            mode = 'markers+text',
                            marker = dict(
                                    symbol = 'circle-dot',
                                    size = 18, 
                                    color = '#6175c1',    #'#DB4551', 
                                    line = dict(color = 'rgb(50,50,50)', width = 1)
                                ),
                            textposition = 'top center',
                            textfont = dict(
                                    family = 'sans serif',
                                    size = 32,
                                    color = '#ff7f0e'
                                )
                        ),
                    dict(
                            x = line_x,
                            y = line_y,
                            mode = 'lines',
                            line = dict(color='rgb(0,0,0)', width=1),
                            hoverinfo = 'none'
                        )
                ]
        )
    layout = dict(
            title = "Synchronization statistics",
            titlefont = dict(size = 18),
            xaxis = dict(
                    title = 'Date Time',
                    nticks = 4,
                    titlefont = dict(size = 18),
                    tickfont = dict(size = 18)
                ),
            yaxis = dict(
                    ticksuffix = '',
                    title = 'layers',
                    titlefont = dict(size = 18),
                    tickfont = dict(size = 18)
                ),
            legend = dict(
                    font = dict(size = 18)
                )
        )

    graph_json = json.dumps(graph, cls=plotly.utils.PlotlyJSONEncoder)
    layout_json = json.dumps(layout, cls=plotly.utils.PlotlyJSONEncoder)

    # Only work online mode
    #figure = Figure(data=graph, layout=layout)
    #plotly.plotly.image.save_as(figure, filename='tmp/'+city, format='jpeg')

    return render_template("sync_statistics.html", graph_json=graph_json, layout_json=layout_json)
