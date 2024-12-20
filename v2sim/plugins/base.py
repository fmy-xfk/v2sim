from abc import abstractmethod
import enum
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Generic, Optional, Protocol, TypeVar, runtime_checkable
from feasytools import RangeList
from fpowerkit import Grid
from ..traffic import TrafficInst
from ..locale import Lang

class PluginStatus(enum.IntEnum):
    '''Plugin status'''
    EXECUTE = 0     # Current call should execute the plugin
    HOLD = 1        # Current call should retain the result of the last plugin execution
    OFFLINE = 2     # Current call should return the return value when the plugin is offline

PIResult = TypeVar('PIResult',covariant=True)
PIExec = Callable[[int,PluginStatus],tuple[bool,PIResult]]
PINoRet = Callable[[],None]

@runtime_checkable
class IGridPlugin(Protocol):
    @property
    def Grid(self) -> Grid:
        '''Get the grid instance'''
        raise NotImplementedError

class PluginBase(Generic[PIResult]):
    __PreSimulation: Optional[PINoRet]
    __PreStep: Optional[PIExec]
    __PostSimulation: Optional[PINoRet]
    __PostStep: Optional[PIExec]
    def SetPreSimulation(self,func:PINoRet)->None:
        '''Pre-simulation plugin processing, run after other parameters are loaded'''
        self.__PreSimulation = func
    def SetPreStep(self,func:PIExec)->None:
        '''Plugin work before simulation step'''
        self.__PreStep = func
    def SetPostStep(self,func:PIExec)->None:
        '''Plugin work after simulation step'''
        self.__PostStep = func
    def SetPostSimulation(self,func:PINoRet)->None:
        '''Post-simulation plugin processing'''
        self.__PostSimulation = func

    def __init__(self,inst:TrafficInst,elem:ET.Element,work_dir:Path,res_dir:Path,enable_time:Optional[RangeList]=None,
            interval:int=0,plugin_dependency:'list[PluginBase]'=[]):
        '''
        Initialize the plugin
            inst: Traffic network simulation instance
            elem: Plugin configuration XML element
            enable_time: Enable time of the plugin, if not specified, check the online subnode in xml, 
                if the online subnode does not exist, it means always enable
            interval: Plugin running interval, unit = second, 
                if not specified, the invterval attribute must be specified in xml
            plugin_dependency: Plugin dependency list
        '''
        self.__PreStep = None
        self.__PostStep = None
        self.__PreSimulation = None
        self.__PostSimulation = None
        self.__lastTpre = self.__lastTpost = -1
        self.__lastOkpre = False
        self.__lastOkpost = False
        self.__name = elem.tag
        self.__interval = interval if interval > 0 else int(elem.attrib.pop("interval",0))
        if self.__interval <= 0: 
            raise ValueError(Lang.ERROR_PLUGIN_INTERVAL)
        self.__on = enable_time
        if self.__on is None:
            online_elem = elem.find("online")
            if online_elem is None: self.__on = None
            else: self.__on = RangeList(online_elem)
        self.__respre = self.__respost = self.Initialization(elem,inst,work_dir,res_dir,plugin_dependency)
    
    @property
    @abstractmethod
    def Description(self)->str:
        '''Get the plugin description'''
        raise NotImplementedError
    
    @property
    def Name(self)->str:
        '''Get the plugin name'''
        return self.__name
    
    @property
    def Interval(self)->int:
        '''Get the plugin running interval, unit = second'''
        return self.__interval
    
    @property
    def OnlineTime(self)->Optional[RangeList]:
        '''Get the plugin enable time'''
        return self.__on
    
    @property
    def LastTime(self)->int:
        '''
        Get the time when the last plugin was in PluginStatus.EXECUTE state
        '''
        return self.__lastTpre
    
    @property
    def LastPreStepSucceed(self)->bool:
        '''
        Get whether PreStep was successful when the last plugin was in PluginStatus.EXECUTE state
        '''
        return self.__lastOkpre
    
    @property
    def LastPostStepSucceed(self)->bool:
        '''
        Get whether PostStep was successful when the last plugin was in PluginStatus.EXECUTE state
        '''
        return self.__lastOkpost

    @property
    def LastPreStepResult(self)->PIResult:
        '''
        Get the result of PreStep when the last plugin was in PluginStatus.EXECUTE state
        '''
        return self.__respre
    
    @property
    def LastPostStepResult(self)->PIResult:
        '''
        Get the result of PostStep when the last plugin was in PluginStatus.EXECUTE state
        '''
        return self.__respost
    
    @abstractmethod
    def Initialization(self,elem:ET.Element,inst:TrafficInst,work_dir:Path,res_dir:Path,plugin_dependency:'list[PluginBase]') -> PIResult:
        '''
        Initialize the plugin from the XML element, TrafficInst, work path, result path, and plugin dependency.
        Return the result of offline.
        '''
    
    def IsOnline(self,t:int):
        '''Determine if the plugin is online'''
        return self.__on is None or t in self.__on
    
    def _presim(self)->None:
        '''Run the plugin PreSimulation'''
        if self.__PreSimulation is not None:
            self.__PreSimulation()
    
    def _postsim(self)->None:
        '''Run the plugin PostSimulation'''
        if self.__PostSimulation is not None:
            self.__PostSimulation()
    
    def _precall(self,_t:int)->None:
        '''Run the plugin PreStep'''
        if self.__PreStep is None: return
        if self.__on != None and _t not in self.__on:
            self.__PreStep(_t,PluginStatus.OFFLINE)
        elif self.__lastTpre + self.__interval <= _t or self.__lastTpre < 0:
            self.__lastOkpre, self.__respre = self.__PreStep(_t,PluginStatus.EXECUTE)
            self.__lastTpre = _t
        else:
            self.__PreStep(_t,PluginStatus.HOLD)
    
    def _postcall(self,_t:int,/)->None:
        '''Run the plugin PostStep'''
        if self.__PostStep is None: return
        if self.__on != None and _t not in self.__on:
            self.__PostStep(_t,PluginStatus.OFFLINE)
        elif self.__lastTpost + self.__interval <= _t or self.__lastTpost < 0:
            self.__lastOkpost, self.__respost = self.__PostStep(_t,PluginStatus.EXECUTE)
            self.__lastTpost = _t
        else:
            self.__PostStep(_t,PluginStatus.HOLD)