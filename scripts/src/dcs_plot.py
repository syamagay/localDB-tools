# Author : Shohei Yamagata(Osaka univ.)

from pymongo import MongoClient
import sys, json, collections, os, pwd
from array import array
from bson.objectid import ObjectId
from datetime import datetime
import time
from flask import session 

import ROOT
ROOT.gROOT.SetBatch()
canvas=ROOT.TCanvas('canvas','')

from scripts.src.PlotTools import pyPlot as plt

dcs_key_list=[
    'vddd',
    'vdda',
    'hv'
]

iv_key_list=[
    {
        'name'  : 'vddd',
        'key_v' : 'vddd_voltage',
        'key_i' : 'vddd_current',
        'num'   : 0
    },
    {
        'name'  : 'vdda',
        'key_v' : 'vdda_voltage',
        'key_i' : 'vdda_current',
        'num'   : 0
    },
    {
        'name'  : 'hv',
        'key_v' : 'hv_voltage',
        'key_i' : 'hv_current',
        'num'   : 0
    }
]
other_key_list=[
    {
        'key' : 'temperature',
        'num' : 0
    },
    {
        'key' : 'temperature',
        'num' : 1
    }
]
Graph_yrange={
    "vddd_voltage" : [ -0.2 , 2.0 , 0.1 ],
    "vddd_current" : [ -0.2 , 1.0 , 0.1 ],
    "vdda_voltage" : [ -0.2 , 2.0 , 0.1 ],
    "vdda_current" : [ -0.2 , 1.0 , 0.1 ],
    "hv_voltage"   : [-100.0, 10.0 , 1.0],
    "hv_current"   : [-7.0E-6,1.0E-6,1.0E-6],
    "temperature"  : [ -40.0, 40.0, 1.0 ]
}

class DCS_type(object):
    def __init__(self,data_block=None):
        self.startTime=0
        self.finishTime=0
        if  data_block:
            self.__dcs_data=data_block
    def get_entry(self,key,num):
        try :
            return len(self.__dcs_data[key][num]['data'])
        except :
            return None
    def get_description(self,key,num):
        return self.__dcs_data[key][num]['description']
    def get_single_data(self,key,num,i):
        data_time=0
        try :
            data=float(self.__dcs_data[key][num]['data'][i]['value'])
        except :
            data=None
        else :
            data_time=time.mktime(self.__dcs_data[key][0]['data'][i]['date'].timetuple())
        return data_time, data
    def set_RunTime(self, start, finish):
        self.startTime=start
        self.finishTime=finish
    def set_timeRange(self, time1, time2):
        self.timeRange=[time1,time2]
        
def make_dir(DIR):
    if not os.path.isdir(DIR) :
        os.mkdir( DIR )

def make_Graph(DCS, key, num):
    picture_DIR='/tmp/{0}/{1}/dcs/'.format( pwd.getpwuid( os.geteuid() ).pw_name , session.get('uuid','localuser') )
    picture_type='.png'
    make_dir( picture_DIR )

    ROOT.gStyle.SetTimeOffset(-788918400)
    ROOT.gStyle.SetNdivisions(505)
    GraphStat={}
    
    i_Entry=0
    data=''
    data_min=0;
    data_max=0;

    if DCS.get_entry(key,num) == None :
        return None

    g=ROOT.TGraph(DCS.get_entry(key,num))
    while data != None :
        data_time,data=DCS.get_single_data(key,num,i_Entry)
        if data == None :
            break
        g.SetPoint(i_Entry,data_time,data)
        if data_max < data :
            data_max=data
        if data_min > data :
            data_min=data
        i_Entry=i_Entry+1
    g.SetName(key)
    g.SetTitle(key+';'+'time'+';'+DCS.get_description(key,num))

    if session['dcsStat'].get( key ) :
        y_min=float(session['dcsStat'][key].get('min'))
        y_max=float(session['dcsStat'][key].get('max'))
        step =float(session['dcsStat'][key].get('step'))
    elif Graph_yrange.get(key) :
        y_min=Graph_yrange[key][0]
        y_max=Graph_yrange[key][1]
        step =Graph_yrange[key][2]
    else :
        y_min=data_min
        y_max=data_max
        step =1

    g.SetMinimum(y_min)
    g.SetMaximum(y_max)

    g.GetXaxis().SetLimits(DCS.timeRange[0],DCS.timeRange[1])
    g.GetXaxis().SetTimeDisplay(1)
    g.GetXaxis().SetTimeFormat("%H:%M:%S")
 

    box=ROOT.TBox(DCS.startTime,y_min,DCS.finishTime,y_max)
    box.SetFillStyle(3004)
    box.SetFillColor(2)

    canvas.cd()
    g.Draw('APL')
    box.Draw('same')
    
    filename=picture_DIR+key+picture_type
    
    canvas.Print(filename)
 
    GraphStat={ 'filename' : filename,
                'max'      : y_max,
                'min'      : y_min,
                'step'     : step
    }

    return GraphStat

## This comment out is  tool to plot Graph of dcs data with matplotlib
## comment out : 2019/07/07 by Yamagaya
"""
def make_Graph_with_matplotlib(DCS, key, num):
    picture_DIR='/tmp/{0}/{1}/dcs/'.format( pwd.getpwuid( os.geteuid() ).pw_name , session.get('uuid','localuser') )
    picture_type='.png'
    make_dir( picture_DIR )

    GraphStat={}
    
    i_Entry=0
    data=''
    data_min=0;
    data_max=0;

    if DCS.get_entry(key,num) == None :
        return None
    c=plt.pyCanvas()
    g=plt.pyGraph()
    g.SetCanvas(c)
    while data != None :
        data_time,data=DCS.get_single_data(key,num,i_Entry)
        if data == None :
            break
        data_time=datetime.fromtimestamp(data_time)
        g.SetPoint(data_time,data)
        if data_max < data :
            data_max=data
        if data_min > data :
            data_min=data
        i_Entry=i_Entry+1
    g.SetTitle(key)
    g.SetXAxisTitle('time')
    g.SetYAxisTitle(DCS.get_description(key,num))

    if session['dcsStat'].get( key ) :
        y_min=float(session['dcsStat'][key].get('min'))
        y_max=float(session['dcsStat'][key].get('max'))
        step =float(session['dcsStat'][key].get('step'))
    elif Graph_yrange.get(key) :
        y_min=Graph_yrange[key][0]
        y_max=Graph_yrange[key][1]
        step =Graph_yrange[key][2]
    else :
        y_min=data_min
        y_max=data_max
        step =1

    g.SetYRange(y_min,y_max)
    g.SetXRange(datetime.fromtimestamp(DCS.timeRange[0]),datetime.fromtimestamp(DCS.timeRange[1]))
    g.SetXAxis_Time()
    g.SetXRegion(datetime.fromtimestamp(DCS.startTime),datetime.fromtimestamp(DCS.finishTime))
    g.Draw()
    
    filename=picture_DIR+key+picture_type
    c.Print(filename)
 
    GraphStat={ 'filename' : filename,
                'max'      : y_max,
                'min'      : y_min,
                'step'     : step
    }

    return GraphStat
""" 
def dcs_plot( data_block, startTime, finishTime, dcsPlot ):
    timeRange=session['dcsStat'].get('timeRange')
    DCS=DCS_type(data_block)
    DCS.set_RunTime(startTime,finishTime)
    DCS.set_timeRange(timeRange[0],timeRange[1])
    for i_key in iv_key_list :
        PlotType=i_key['name']
        key_v=i_key['key_v']
        key_i=i_key['key_i']
        key_num=i_key['num']
        GraphStat_v=make_Graph(DCS,key_v,key_num)
        GraphStat_i=make_Graph(DCS,key_i,key_num)
        if GraphStat_v!=None and GraphStat_i != None :
            dcsPlot.update({ PlotType :{ 'file_num' : 2,
                                         'filename' : [GraphStat_v.get('filename'),GraphStat_i.get('filename')],
                                         'keyName'  : [key_v,key_i],
                                         'v_min'    : GraphStat_v.get('min'),
                                         'v_max'    : GraphStat_v.get('max'),
                                         'v_step'   : GraphStat_v.get('step'),
                                         'i_min'    : GraphStat_i.get('min'),
                                         'i_max'    : GraphStat_i.get('max'),
                                         'i_step'   : GraphStat_i.get('step')
                                     }
                         })

    for i_key in other_key_list :
        key=i_key['key']
        key_num=i_key['num']
        GraphStat=make_Graph(DCS,key,key_num)
        if GraphStat!=None :
            dcsPlot.update({ key :{ 'file_num' : 1,
                                    'filename' : [GraphStat.get('filename')],
                                    'min'      : GraphStat.get('min'),
                                    'max'      : GraphStat.get('max'),
                                    'step'     : GraphStat.get('step')
                                }
                         })
    return dcsPlot
    
if __name__=='__main__':
    dcs_plot()
