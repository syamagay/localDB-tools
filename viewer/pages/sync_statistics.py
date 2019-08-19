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

    def __check_dup(x_list, y_list, x, y):
        if x in x_list and y in y_list: return True
        else: return False

    def __getCommitRelationship(commit_doc, marker_x, marker_y, line_x, line_y):
        while True:
            #==========================
            # parent --- child
            #==========================
            # Get child layer
            if commit_doc["local_server_config_id"] in layer_list:
                child_layer = layer_list.index(commit_doc["local_server_config_id"])
            else:
                layer_list.append(commit_doc["local_server_config_id"])
                child_layer = len(layer_list) - 1

            # child
            if __check_dup(marker_x, marker_y, commit_doc["sys"]["cts"], child_layer): break
            marker_x.append(commit_doc["sys"]["cts"])
            marker_y.append(child_layer)
            commit_description.append("_id: %s" % str(commit_doc["_id"]))

            # Get parent layer
            if commit_doc["parent"] == "": break
            commit_description[-1] = commit_description[-1] + "<br>parent: %s" % str(commit_doc["parent"])
            parent_commit_doc = localdbtools_db["commits"].find_one({"_id": commit_doc["parent"]})
            if parent_commit_doc["local_server_config_id"] in layer_list:
                parent_layer = layer_list.index(parent_commit_doc["local_server_config_id"])
            else:
                layer_list.append(parent_commit_doc["local_server_config_id"])
                parent_layer = len(layer_list) - 1

            # line between parent and child
            line_x.append(commit_doc["sys"]["cts"])
            line_y.append(child_layer)
            line_x.append(parent_commit_doc["sys"]["cts"])
            line_y.append(parent_layer)
            line_x.append(None)
            line_y.append(None)

            #==========================
            # parent ---------- child
            #                |
            # parent_merge ---
            #==========================
            if commit_doc["commit_type"] == "merge" and commit_doc["parent_merge"] != "":
                commit_description[-1] = commit_description[-1] + "<br>parent_merge: %s" % str(commit_doc["parent_merge"])
                # Get parent merge layer
                parent_merge_commit_doc = localdbtools_db["commits"].find_one({"_id": commit_doc["parent_merge"]})
                if parent_merge_commit_doc["local_server_config_id"] in layer_list:
                    parent_merge_layer = layer_list.index(parent_merge_commit_doc["local_server_config_id"])
                else:
                    layer_list.append(parent_merge_commit_doc["local_server_config_id"])
                    parent_merge_layer = len(layer_list) - 1

                # line between parent_merge and child
                line_x.append(commit_doc["sys"]["cts"])
                line_y.append(child_layer)
                line_x.append(parent_merge_commit_doc["sys"]["cts"])
                line_y.append(parent_merge_layer)
                line_x.append(None)
                line_y.append(None)
                #merge_count += 1
                __getCommitRelationship(parent_merge_commit_doc, marker_x, marker_y, line_x, line_y)

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
    layer_list = []
    __getCommitRelationship(last_commit_doc, marker_x, marker_y, line_x, line_y)

    logging.debug("maker length: %d" % len(marker_x))
    #for i in range(len(marker_x)):
    #    logging.debug("marker (%s, %s)" % (str(marker_x[i]), str(marker_y[i])))
    logging.debug("line length: %d" % len(line_x))
    #for i in range(len(line_x)):
    #    logging.debug("i: %d, line (%s, %s)" % (i, str(line_x[i]), str(line_y[i])) )

    graph = dict(
            data = [
                    dict(
                            x = marker_x,
                            y = marker_y,
                            text = commit_description,
                            type ="scatter",
                            name = "commits",
                            mode = 'markers',
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
