import numpy as np
import matplotlib
from matplotlib import pyplot 
from matplotlib import dates as mdates

class pyGraph :
    def __init__(self, title=None ) :
        self.__Title=title
        self.__xTitle=None
        self.__yTitle=None
        self.__x_min=None
        self.__x_max=None
        self.__y_min=None
        self.__y_max=None

        self.__setRegion=False
        self.__RegionXmin=None
        self.__RegionXmax=None
        self.__RegionYmin=None
        self.__RegionYmax=None

        self.__setXAxis_time=False
        
        self.__x_list=np.array( [] )
        self.__y_list=np.array( [] )
        
        self.__canvas=gPad
    def SetPoint( self, x , y ) :
        self.__x_list=np.append( self.__x_list ,x )
        self.__y_list=np.append( self.__y_list ,y )
    def GetxList(self) :
        return self.__x_list
    def GetyList(self) :
        return self.__y_list
    def GetEntries(self) :
        return len(self.__x_list)
    def SetCanvas(self,canvas):
        self.__canvas=canvas
    def SetTitle(self, string) :
        self.__Title=string
    def SetXAxisTitle(self, string) :
        self.__xTitle=string
    def SetYAxisTitle(self, string) :
        self.__yTitle=string
    def SetXRange(self, x_min ,x_max) :
        self.__x_min=x_min
        self.__x_max=x_max
    def SetYRange(self, y_min , y_max) :
        self.__y_min=y_min
        self.__y_max=y_max
    def SetXAxis_Time(self) :
        self.__setXAxis_time=True
    def SetXRegion(self , x_min,x_max) :
        self.__setRegion=True
        self.__RegionXmin=x_min
        self.__RegionXmax=x_max
    def Draw(self) :
        if not self.__Title == None : self.__canvas.ax.set_title(self.__Title)
        if not self.__xTitle == None : self.__canvas.ax.set_xlabel(self.__xTitle)
        if not self.__yTitle == None : self.__canvas.ax.set_ylabel(self.__yTitle)

        if self.__x_min==None and self.__x_max==None :
            self.__x_min=np.amin(self.__x_list)
            self.__x_max=np.amax(self.__x_list)
        if self.__y_min==None and self.__y_max==None :
            self.__y_min=np.amin(self.__y_list)
            self.__y_max=np.amax(self.__y_list)
        
        self.__canvas.ax.set_xlim(self.__x_min,self.__x_max)
        self.__canvas.ax.set_ylim(self.__y_min,self.__y_max)

        if self.__setXAxis_time==True :
            self.__canvas.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        if self.__setRegion==True :
            if self.__RegionXmin==None : self.__RegionXmin = self.__x_min
            if self.__RegionXmax==None : self.__RegionXmax = self.__x_max
            if self.__RegionYmin==None : self.__RegionYmin = self.__y_min
            if self.__RegionYmax==None : self.__RegionYmax = self.__y_max
            rangeX = [ self.__RegionXmin, self.__RegionXmin, self.__RegionXmax, self.__RegionXmax ]
            rangeY = [ self.__RegionYmin, self.__RegionYmax, self.__RegionYmax, self.__RegionYmin ]
            self.__canvas.ax.fill(rangeX,rangeY,facecolor='r',alpha=0.3)
            
        p=self.__canvas.ax.plot(self.__x_list,self.__y_list,marker='o')
        self.__canvas.output(p)
        

class pyCanvas :
    def __init__(self) :
        self.__plotlist=[]
        self.__old_plot=None
        self.fig=pyplot.figure(figsize=(10,8))
        self.ax = self.fig.add_subplot(111)

        self.permit_show=False
    def output(self , p) :
        self.__old_plot=None
        self.__old_plot=p
        if self.permit_show == True :
            pyplot.show()
        
    def output_withregion(self,p) :
        pyplot.legend((self.__old_plot[0],p[0]),("Plot1","Plot2"),loc=4)
    def Print(self, filename) :
        pyplot.savefig(filename)

#### gloabl instance #############
gPad=pyCanvas()

def main() :
    g=pyGraph()
    g.SetPoint(1,1)
    g.SetPoint(2,2)
    g.SetPoint(3,3)
    g.SetTitle('gayaGraph')
    g.SetYRange(0,100)
    g.SetXRegion(1.5,2.0)
    g.Draw()
    print(g.GetEntries())
    

if __name__=='__main__' :
    gPad.permit_show=True
    main()
