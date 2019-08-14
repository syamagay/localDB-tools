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

#from scripts.src.PlotTools import pyPlot as plt

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
dat_row=['dcsType',
         'num',
         'chipname',
         'description']
class DCS_type(object):
    def __init__(self,dcsPlotList):
        self.startTime=0
        self.finishTime=0
        
        
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
            data_time=self.__dcs_data[key][0]['data'][i]['date']
            data_time=time.mktime(data_time.timetuple())
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
    g.SetTitle(key+';'+'time(UTC)'+';'+DCS.get_description(key,num))

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
def make_dcsGraph(dat):
    ROOT.gStyle.SetTimeOffset(-788918400)
    ROOT.gStyle.SetNdivisions(505)

    timeRange=session['dcsStat'].get('timeRange')
    with open(dat,'r') as f :
        datStatus={}
        timestamp_list=[]
        value_list=[]
        for line, readline in enumerate(f.readlines()):
            if line < len(dat_row):
                datStatus.update({dat_row[line]:readline})
            elif line >= len(dat_row):
                data=readline.split()
                timestamp_list.append(float(data[0]))
                value_list.append(float(data[1]))
    entry_num=len(timestamp_list)
    dcsType=datStatus.get('dcsType').rstrip('\n')
    if not entry_num == len(value_list):
        return None
    graph=ROOT.TGraph(entry_num)
    title=str(datStatus.get('dcsType'))+';Time(UTC);'+str(datStatus.get('description'))
    graph.SetTitle(title)
    entry=0
    data_min=0
    data_max=0
    for timestamp, value in zip(timestamp_list,value_list):
        graph.SetPoint(entry,timestamp,value)
        if data_max < value :
            data_max=value
        if data_min > value :
            data_min=value

        entry+=1
    if session['dcsStat'].get( dcsType ) :
        y_min=float(session['dcsStat'][dcsType].get('min'))
        y_max=float(session['dcsStat'][dcsType].get('max'))
        step =float(session['dcsStat'][dcsType].get('step'))
    elif Graph_yrange.get( dcsType ) :
        y_min=Graph_yrange[dcsType][0]
        y_max=Graph_yrange[dcsType][1]
        step =Graph_yrange[dcsType][2]
    else :
        y_min=data_min
        y_max=data_max
        step =1

    graph.SetMinimum(y_min)
    graph.SetMaximum(y_max)

    graph.GetXaxis().SetLimits(timeRange[0],timeRange[1])
    graph.GetXaxis().SetTimeDisplay(1)
    graph.GetXaxis().SetTimeFormat("%H:%M:%S")

    graph_stat={'graph' : graph,
                'min'   : y_min,
                'max'   : y_max,
                'step'  : step}
    return graph_stat

def make_dcsPlot(num, dcsType, dat_list):
    RunTime=session['dcsStat'].get('RunTime')
    picture_DIR='/tmp/{0}/{1}/dcs/plot/'.format( pwd.getpwuid( os.geteuid() ).pw_name , session.get('uuid','localuser') )
    picture_type='.png'
    make_dir( picture_DIR )

    graph_list=[]
    dat_num=0
    for dat in dat_list :
        graph_stat=make_dcsGraph(dat)
        graph=graph_stat.get('graph')
        if not graph is None :
            graph_list.append(graph)
        if dat_num == 0 :
            y_min=graph_stat.get('min')
            y_max=graph_stat.get('max')
            step=graph_stat.get('step')
        dat_num += 1
    canvas=ROOT.TCanvas('canvas','')
    gr_num=1
    for gr in graph_list :
        gr.SetLineColor(gr_num)
        gr.SetMarkerColor(gr_num)
        if gr_num == 1 :
            gr.Draw('APL');
        else :
            gr.Draw('PL')
        gr_num+=1
    box=ROOT.TBox(RunTime[0],y_min,RunTime[1],y_max)
    box.SetFillStyle(3004)
    box.SetFillColor(2)
    box.Draw('same')
    picture_path=str(picture_DIR)+str(dcsType)+'-'+str(num)+str(picture_type)
    canvas.Print(picture_path)
    GraphStat={ 'filename' : picture_path,
                'max'      : y_max,
                'min'      : y_min,
                'step'     : step
    }

    return GraphStat


def dcs_plot( dcsPlotList ):
    dcsPlot={}
    for i_key in iv_key_list :
        PlotType=i_key['name']
        key_v=i_key['key_v']
        key_i=i_key['key_i']
        key_num=i_key['num']
        v_dat_list=[]
        i_dat_list=[]
        if not dcsPlotList.get(key_v) is None and not dcsPlotList.get(key_i) is None :
            for num in dcsPlotList[key_v] :
                for chip in dcsPlotList[key_v][num] :
                    v_dat_list.append(dcsPlotList[key_v][num][chip].get('dat'))
                    i_dat_list.append(dcsPlotList[key_i][num][chip].get('dat'))
                GraphStat_v=make_dcsPlot(num, key_v, v_dat_list)
                GraphStat_i=make_dcsPlot(num, key_i, i_dat_list)
                if GraphStat_v!=None and GraphStat_i != None :
                    dcsPlot.update({ PlotType+'-'+str(num) :{ 'file_num' : 2,
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
        dat_list=[]
        if not dcsPlotList.get(key) is None :
            for num in dcsPlotList[key] :
                for chip in dcsPlotList[key][num]:
                    dat_list.append(dcsPlotList[key_v][num][chip].get('dat'))
                GraphStat=make_dcsGraph(num, key,dat_list)
                if not GraphStat is None :
                    dcsPlot.update({ key+'-'+str(num) :{ 'file_num' : 1,
                                                        'filename' : [GraphStat.get('filename')],
                                                        'min'      : GraphStat.get('min'),
                                                        'max'      : GraphStat.get('max'),
                                                        'step'     : GraphStat.get('step')
                                        }
                                 })
    return dcsPlot
    
if __name__=='__main__':
    dcs_plot()
