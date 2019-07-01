# Author : Shohei Yamagata(Osaka univ.)

import ROOT
from pymongo import MongoClient
import sys, json, collections, os, pwd
from array import array
from bson.objectid import ObjectId
from datetime import datetime
import time
from flask import session 

class DCS_type(object):
    def __init__(self,data_block=None):
        if  data_block:
            self.__dcs_data=data_block
       
        if self.__dcs_data:
            self.candidate=['hv','VDDD','VDDA','share','vddd','vdda'] # gaya format
            self.__type=self.get_dcsdata_list()
            self.__type_num=len(self.__type)
            if self.__type_num>0 :
                self.__event_num=self.get_event_num()
    def set_candidate(self):
        return self.candidate
    def set_data_tag(self):
        return self.data_tag
    def get_dcsdata_source(self):
        data=self.obj.read_one()
        if data :
            return data
        else :
            return None
    def get_dcsdata_list(self):
        type=[]
        for candidate in self.candidate:
            if candidate+'_voltage' in self.__dcs_data:
                type.append(candidate)
        return type
    def get_type_num(self):
        return self.__type_num
    def get_event_num(self):
        return len(self.__dcs_data[self.__type[0]+'_voltage'][0]['data'])
    def data_exist(self) :
        if self.__dcs_data and self.__type_num > 0 :
            return True
        else :
            return False
    def get_graph_yrange(self,dcsType) :
        if dcsType == 'hv' :
            return [-100.0,10.0],[-7.0E-6,1.0E-6]
        elif dcsType == 'share' :
            return [-0.2,4.0],[-0.2,2.2]
        else :
            return [-0.2,2.0],[-0.2,0.7]
    def get_graph_step(self,dcsType) :
        if dcsType == 'hv' :
            return 1,1E-6
        elif dcsType == 'share' :
            return 0.1,0.1
        else :
            return 0.1,0.1

    def get_single_value(self,i):
        voltage=[]
        current=[]
        i_type_count=0
    
        data_time=time.mktime(self.__dcs_data['hv_voltage'][0]['data'][i]['date'].timetuple()) 
        for i_type in self. __type:
            voltage.append(float(self.__dcs_data[i_type+'_voltage'][0]['data'][i]['value']))
            current.append(float(self.__dcs_data[i_type+'_current'][0]['data'][i]['value']))

        return voltage, current, data_time
        
def make_dir(DIR):
    if not os.path.isdir(DIR) :
        os.mkdir( DIR )

#def dcs_plot( runId ):
def dcs_plot( data_block, startTime, finishTime ):
    ROOT.gStyle.SetTimeOffset(-788918400)
    ROOT.gStyle.SetNdivisions(505)

    graph_v=[]
    graph_i=[]
    c=[]

    picture_DIR='/tmp/{}/dcs/'.format( pwd.getpwuid( os.geteuid() ).pw_name )
    picture_type='.png'
#    make_dir( picture_DIR )
    
    DCS=DCS_type(data_block)
    
    if DCS.data_exist() :
        if not session.get( 'dcsList' ):
            session['dcsList']={}
        dcs_list=DCS.get_dcsdata_list()
        num=DCS.get_event_num()
        v_min=[]
        v_max=[]
        i_min=[]
        i_max=[]

        if session.get('dcsRange') and not session.get('dcsplotType')=='set_TimeRange' :
            TimeRange=[session['dcsRange'].get('start'),session['dcsRange'].get('end')]
        else:
            TimeRange=[startTime-10,finishTime+10]

        for dcsType in dcs_list :
            if session['dcsList'].get(dcsType) and session['dcsList'][dcsType].get('Parameter') and not session.get( 'dcsplotType' )=='set' :
                v_min.append(float(session['dcsList'][dcsType]['Parameter'].get('v_min')))
                v_max.append(float(session['dcsList'][dcsType]['Parameter'].get('v_max')))
                i_min.append(float(session['dcsList'][dcsType]['Parameter'].get('i_min')))
                i_max.append(float(session['dcsList'][dcsType]['Parameter'].get('i_max')))
                
            else :
                v_graph_yrange,i_graph_yrange=DCS.get_graph_yrange(dcsType)
                v_min.append(v_graph_yrange[0])
                v_max.append(v_graph_yrange[1])
                i_min.append(i_graph_yrange[0])
                i_max.append(i_graph_yrange[1])
        for j in range(0,DCS.get_event_num()):
            voltage, current, data_time=DCS.get_single_value(j)
            for i in range(0,DCS.get_type_num()):
                if j==0 :
                    c.append(ROOT.TCanvas("c_"+str(i),""))
                    graph_v.append(ROOT.TGraph())
                    graph_v[i].SetName('graph_v'+str(i))
                    graph_i.append(ROOT.TGraph())
                    graph_i[i].SetName('graph_i'+str(i))

                graph_v[i].SetPoint(j,data_time,voltage[i])
                graph_i[i].SetPoint(j,data_time,current[i])        

        session['RunTime']={"Runstart"  : datetime.fromtimestamp(float(startTime)),
                            "Runfinish" : datetime.fromtimestamp(float(finishTime))}
        
        for i in range(0,DCS.get_type_num()):
            c[i].cd()
            dcsType=dcs_list[i]
            filename_v=picture_DIR+dcsType+'_v'+str(i)+picture_type
            filename_i=picture_DIR+dcsType+'_i'+str(i)+picture_type
            
            v_step,i_step=DCS.get_graph_step(dcsType)
            
            graph_v[i].SetMinimum(v_min[i])
            graph_v[i].SetMaximum(v_max[i])
            graph_i[i].SetMinimum(i_min[i])
            graph_i[i].SetMaximum(i_max[i])

            box_v=ROOT.TBox(startTime,v_min[i],finishTime,v_max[i])

            box_v.SetFillStyle(3004)
            box_v.SetFillColor(2)

            graph_v[i].GetXaxis().SetTimeDisplay(1)
            graph_v[i].GetXaxis().SetLimits(TimeRange[0],TimeRange[1])
            graph_v[i].GetXaxis().SetTimeFormat("%H:%M:%S")
            graph_v[i].GetXaxis().SetTitle("Times")
            graph_v[i].GetYaxis().SetTitle("Voltage[V]")
            graph_v[i].Draw('APL')
            box_v.Draw('SAME')
            
            c[i].Print(filename_v)

            box_i=ROOT.TBox(startTime,i_min[i],finishTime,i_max[i])
            box_i.SetFillStyle(3004)
            box_i.SetFillColor(2)

            graph_i[i].GetXaxis().SetTimeDisplay(1)
            graph_i[i].GetXaxis().SetLimits(TimeRange[0],TimeRange[1])
            graph_i[i].GetXaxis().SetTimeFormat("%H:%M:%S")
            graph_i[i].GetXaxis().SetTitle("Times")
            graph_i[i].GetYaxis().SetTitle("Current[A]")
            graph_i[i].Draw('APL')
            box_i.Draw('SAME')
            c[i].Print(filename_i)

            session['dcsList'].update({dcsType : {"voltage_f": filename_v,
                                                  "current_f": filename_i,
                                                  "time"     : {"start" : datetime.fromtimestamp(TimeRange[0]),
                                                                "end"   : datetime.fromtimestamp(TimeRange[1])},
                                                  "Parameter":{"v_min"    : v_min[i],
                                                               "v_max"    : v_max[i],
                                                               "i_min"    : i_min[i],
                                                               "i_max"    : i_max[i]},
                                                  "v_step"   : v_step,
                                                  "i_step"   : i_step
                                            }
                                   })
    else :
        session['dcsList']={}
if __name__=='__main__':
    dcs_plot()
