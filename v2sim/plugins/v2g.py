from ..locale import CustomLocaleLib
from fpowerkit import Generator
from feasytools import ComFunc
from .pdn import PluginPDN
from .base import *

V2GRes = list[float]

_locale = CustomLocaleLib(["zh_CN","en"])
_locale.SetLanguageLib("zh_CN",
    DESCRIPTION = "V2G调度系统",
    ERROR_NO_PDN = "V2G调度依赖于PDN插件",
    ERROR_SMART_CHARGE = "启用有序充电时V2G调度插件不可用",
)
_locale.SetLanguageLib("en",
    DESCRIPTION = "V2G scheduling system",
    ERROR_NO_PDN = "V2G scheduling depends on PDN plugin",
    ERROR_SMART_CHARGE = "V2G scheduling plugin is not available when smart charging is enabled",
)

class PluginV2G(PluginBase[V2GRes]):
    @property
    def Description(self)->str:
        return _locale["DESCRIPTION"]
    
    def Initialization(self,elem:ET.Element,inst:TrafficInst,work_dir:Path,res_dir:Path,plugin_dependency:'list[PluginBase]')->V2GRes:
        assert len(plugin_dependency) == 1 and isinstance(plugin_dependency[0], IGridPlugin), _locale["ERROR_NO_PDN"]
        self.__pdn = plugin_dependency[0]
        if isinstance(self.__pdn, PluginPDN) and self.__pdn.isSmartChargeEnabled():
            raise RuntimeError(_locale["ERROR_SMART_CHARGE"])
        self.__inst = inst
        self._cap:list[float] = [0.] * len(inst.SCSList)

        for i,pk in enumerate(inst.SCSList):
            self.__pdn.Grid.AddGen(Generator("V2G_"+pk.name,pk.node,
                0.,ComFunc(self.__get_cap(i)),0.,0.,0.,pk.psell*(self.__pdn.Grid.Sb*1000),0.))
        self.SetPreStep(self._work)
        return []
    
    def __get_cap(self,i:int):
        def func(t: int)->float:
            if not self.IsOnline(t): return 0.
            return self._cap[i]
        return func
   
    def _work(self,_t:int,/,sta:PluginStatus)->tuple[bool,list[float]]:
        '''
        Get the V2G demand power of all bus with slow charging stations at time _t, unit kWh/s, 3.6MW=3600kW=1kWh/s
        '''
        if sta == PluginStatus.EXECUTE:
            if self.__pdn.LastPreStepSucceed:
                self._cap = [x*3.6/self.__pdn.Grid.Sb for x in self.__inst.SCSList.get_V2G_cap(_t)]
                f = lambda x: (0.0 if x is None else x)*self.__pdn.Grid.Sb/3.6
                ret1 = [f(self.__pdn.Grid.Gen("V2G_"+pk.name).P) for pk in self.__inst.SCSList]
                if sum(ret1)>1e-8: ret = True, ret1
                else: ret = False, []
            else:
                ret = False, []
            self.__inst.SCSList.set_V2G_demand(ret[1])
        elif sta == PluginStatus.OFFLINE:
            self.__inst.SCSList.set_V2G_demand([])
            ret = True, []
        elif sta == PluginStatus.HOLD:
            ret = True, self.LastPreStepResult
        return ret