import os
from pathlib import Path
from queue import Empty, Queue
import threading
from typing import Any, Optional
from fgui.network import OAfter
from fgui.view import *
from fgui import ScrollableTreeView, ALWAYS_ONLINE, PDFuncEditor, PropertyPanel, EditMode, NetworkPanel
from tkinter import filedialog
from tkinter import messagebox as MB
from v2sim import *
from fpowerkit import Grid as PowerGrid
from feasytools import RangeList, SegFunc, OverrideFunc, ConstFunc, PDUniform
import xml.etree.ElementTree as ET

DEFAULT_PDN_ATTR = {}
DEFAULT_GRID_NAME = "pdn.grid.xml"
DEFAULT_GRID = '<grid Sb="1MVA" Ub="10.0kV" model="ieee33" fixed-load="false" grid-repeat="1" load-repeat="8" />'

def showerr(msg:str):
    MB.showerror(_loc["MB_ERROR"], msg)

_loc = CustomLocaleLib(["zh_CN","en"])
_loc.SetLanguageLib("zh_CN",
    DONE = "完成",
    BTN_FIND = "查找",
    MB_EXIT_SAVE = "是否要在退出前保存项目？",
    MB_SAVE_AND_SIM = "项目未保存。是否保存并开始仿真？",
    STA_READY = "就绪",
    TITLE = "V2Sim(Python版)项目编辑器",
    LB_COUNT = "数量：{0}",
    MENU_PROJ = "项目",
    MENU_OPEN = "打开...",
    MENU_SAVEALL = "全部保存",
    MENU_EXIT = "退出",
    MENU_LANG = "语言",
    MENU_LANG_AUTO = "(自动选择)",
    MENU_LANG_EN = "English",
    MENU_LANG_ZHCN = "中文(简体)",
    MB_INFO = "提示",
    MB_ERROR = "错误",
    MB_CFG_MODIFY = "SUMO自动生成配置文件与V2Sim平台标准有差异。是否修改SUMO配置文件？\n请注意，这将删除SUMO生成的行程，仅保留V2Sim生成的行程文件。",
    LANG_RESTART = "您需要重新启动本应用程序以切换语言。",
    BAR_PROJINFO = "项目信息",
    BAR_NONE = "无",
    BAR_FCS = "快充站：",
    BAR_SCS = "慢充站：",
    BAR_GRID = "电网：",
    BAR_RNET = "路网：",
    BAR_VEH = "车辆：",
    BAR_PLG = "插件：",
    BAR_SUMO ="SUMO配置：",
    BAR_TAZ = "交通区域描述：",
    BAR_ADDON = "Python附加：",
    BAR_TAZTYPE = "交通区域类型：",
    BAR_OSM = "OpenStreetMap： ",
    BAR_POLY = "建筑轮廓描述：",
    BAR_CSCSV = "充电站CSV描述：",
    CSE_EDGE = "所在道路",
    CSE_SLOTS = "充电桩数量",
    CSE_BUS = "所在母线",
    CSE_X = "x坐标",
    CSE_Y = "y坐标",
    CSE_ONLINE = "启用时间",
    CSE_MAXPC = "最大充电功率/kW",
    CSE_MAXPD = "最大放电功率/kW",
    CSE_PRICEBUY = "用户购电价格",
    CSE_PRICESELL = "用户售电价格",
    CSE_PCALLOC = "充电功率分配方案",
    CSE_PDALLOC = "放电功率分配方案",
    RNET_TITLE = "网络",
    RNET_DRAW = "定位",
    RNET_EDGES = "要定位的道路：",
    SAVE_GRID = "保存电网",
    PU_VALS = "基准电压：{0}kV，基准功率：{1}MVA",
    SIM_BASIC = "基本信息",
    SIM_BEGT = "开始时间/秒：",
    SIM_ENDT = "结束时间/秒：",
    SIM_STEP = "仿真步长/秒：",
    SIM_SEED = "随机化种子：",
    SIM_PLUGIN = "插件",
    SIM_STAT = "统计",
    SIM_FCS = "快充站",
    SIM_SCS = "慢充站",
    SIM_VEH = "车辆",
    SIM_GEN = "发电机",
    SIM_BUS = "母线",
    SIM_LINE = "线路",
    SIM_START = "开始仿真！",
    SIM_PLGNAME = "插件名称",
    SIM_EXEINTV = "执行间隔/秒",
    SIM_ENABLED = "是否启用",
    SIM_PLGOL = "启用时间",
    SIM_PLGPROP = "其他属性",
    SIM_YES = "是",
    SIM_NO = "否",
    SIM_LOAD_LAST_STATE = "加载上次的状态（实验性功能）",
    SIM_SAVE_ON_ABORT = "中断时保存状态",
    SIM_SAVE_ON_FINISH = "仿真结束时保存状态",
    TAB_SIM = "仿真",
    TAB_CSCSV = "充电站下载",
    TAB_FCS = "快充站",
    TAB_SCS = "慢充站",
    TAB_RNET = "网络",
    TAB_VEH = "车辆",
    TAB_GRID = "电网",
    CSCSV_ID = "编号",
    CSCSV_X = "X坐标",
    CSCSV_Y = "Y坐标",
    CSCSV_ADDR = "地址",
    CSCSV_DOWNLOAD = "下载",
    CSCSV_KEY = "高德地图Key：",
    CSCSV_CONFIRM_TITLE = "下载充电站",
    CSCSV_CONFIRM = "是否要从高德地图检索充电站信息？",
    GRID_BASIC = "基本信息",
    GRID_SB = "基准功率:",
    GRID_VB = "基准电压:",
    VEH_BASIC = "基本信息",
    VEH_COUNT = "车辆数量:",
    VEH_V2GPROP = "V2G比例:",
    VEH_V2GPROP_INFO = "愿意参加V2G的电动车比例(0.00~1.00)",
    VEH_SEED = "随机种子:",
    VEH_ODSRC = "OD对来源",
    VEH_ODAUTO = "自动检测",
    VEH_ODTAZ = "根据交通区域类型生成",
    VEH_ODPOLY = "根据建筑轮廓与类型生成",
    VEH_GEN = "生成车辆",
    VEH_OMEGA_DESC = "Omega表示用户对充电成本的敏感度。更大的Omega意味着更小的价格影响。",
    VEH_KREL_DESC = "KRel表示用户对距离的估计。大于1的KRel意味着用户低估了距离。",
    VEH_KSC_DESC = "KSC表示慢充的SoC阈值。",
    VEH_KFC_DESC = "KFC表示半路快充的SoC阈值。",
    VEH_KV2G_DESC = "KV2G表示可用于V2G的电池的SoC阈值。",
    CS_GEN = "生成一组新的充电站",
    CS_MODE = "生成模式",
    CS_USEALL = "所有可用项",
    CS_SELECTED = "指定项目",
    CS_RANDOM = "从所有可用项中抽取N个",
    CS_SRC = "充电站所在道路",
    CS_USEEDGES = "将每条道路都视为可用充电站",
    CS_USECSV = "根据下载的充电站位置判断所在道路",
    CS_USEPOLY = "根据建筑轮廓确定所在道路",
    CS_SLOTS = "充电桩数量",
    CS_SEED = "随机种子",
    CS_PRICEBUY = "用户购电价格",
    CS_PRICESELL = "用户售电价格",
    CS_PB5SEGS = "5段式随机价格",
    CS_PBFIXED = "固定价格",
    CS_BUSMODE = "母线选择方式",
    CS_BUSUSEALL = "在所有可用母线中选择",
    CS_BUSSELECTED = "在给定母线中选择",
    CS_BUSRANDOM = "在N条随机母线中选择",
    CS_BTN_GEN = "生成充电站",
    NOT_OPEN = "未打开",
    SAVED = "已保存",
    UNSAVED = "未保存",
)

_loc.SetLanguageLib("en",
    DONE = "Done",
    BTN_FIND = "Find",
    MB_EXIT_SAVE = "Save the project before exit?",
    MB_SAVE_AND_SIM = "Project not saved. Save the project and start simulation?",
    STA_READY = "Ready",
    TITLE = "V2Sim (Py) Project Editor",
    LB_COUNT = "Count: {0}",
    MENU_PROJ = "Project",
    MENU_OPEN = "Open...",
    MENU_SAVEALL = "Save all",
    MENU_EXIT = "Exit",
    MENU_LANG = "Language",
    MENU_LANG_EN = "English",
    MENU_LANG_ZHCN = "中文(简体)",
    MENU_LANG_AUTO = "(Auto detect)",
    MB_INFO = "Hint",
    MB_ERROR = "Error",
    MB_CFG_MODIFY = "Configuration generated by SUMO automatically is differnet from the standard of V2Sim. Would you like to change the configuration file?\nNOTE: SUMO trips will be removed. Only V2Sim trips will be preserved.",
    LANG_RESTART = "You have to restart this program to change language.",
    BAR_PROJINFO = "Project Information",
    BAR_NONE = "None",
    BAR_FCS = "FCS: ",
    BAR_SCS = "SCS: ",
    BAR_GRID = "Power Grid: ",
    BAR_RNET = "Road Network: ",
    BAR_VEH = "Vehicles: ",
    BAR_PLG = "Plugins: ",
    BAR_SUMO ="SUMO Config: ",
    BAR_TAZ = "TAZ Descriptor: ",
    BAR_ADDON = "Python Add-on: ",
    BAR_TAZTYPE = "TAZ Type: ",
    BAR_OSM = "OpenStreetMap: ",
    BAR_POLY = "Polygon Descriptor: ",
    BAR_CSCSV = "CS CSV Descriptor: ",
    CSE_EDGE = "Edge",
    CSE_SLOTS = "Slots",
    CSE_BUS = "Bus",
    CSE_X = "x",
    CSE_Y = "y",
    CSE_ONLINE = "Online",
    CSE_MAXPC = "Max Pc/kW",
    CSE_MAXPD = "Max Pd/kW",
    CSE_PRICEBUY = "Price Buy",
    CSE_PRICESELL = "Price Sell",
    CSE_PCALLOC = "Pc Allocator",
    CSE_PDALLOC = "Pd Allocator",
    RNET_TITLE = "Network",
    RNET_DRAW = "Locate",
    RNET_EDGES = "Edges to be located:",
    SAVE_GRID = "Save Grid",
    PU_VALS = "Base Voltage: {0}kV, Base Power: {1}MVA",
    SIM_BASIC = "Basic Information",
    SIM_BEGT = "Start Time/s:",
    SIM_ENDT = "End Time/s:",
    SIM_STEP = "Time step/s:",
    SIM_SEED = "Randomize seed:",
    SIM_PLUGIN = "Plugins",
    SIM_STAT = "Statistics",
    SIM_FCS = "FCS",
    SIM_SCS = "SCS",
    SIM_VEH = "Vehicle",
    SIM_GEN = "Generator",
    SIM_BUS = "Bus",
    SIM_LINE = "Line",
    SIM_START = "Start Simulation!",
    SIM_PLGNAME = "Plugin Name",
    SIM_EXEINTV = "Interval/s",
    SIM_ENABLED = "Enabled",
    SIM_PLGOL = "Online Time Range",
    SIM_PLGPROP = "Extra Properties",
    SIM_YES = "Yes",
    SIM_NO = "No",
    SIM_LOAD_LAST_STATE = "Load last state (Experimental)",
    SIM_SAVE_ON_ABORT = "Save state when aborted",
    SIM_SAVE_ON_FINISH = "Save state when simulation ended",
    TAB_SIM = "Simulation",
    TAB_CSCSV = "CS Downloader",
    TAB_FCS = "Fast CS",
    TAB_SCS = "Slow CS",
    TAB_RNET = "Network",
    TAB_VEH = "Vehicles",
    CSCSV_ID = "ID",
    CSCSV_X = "X",
    CSCSV_Y = "Y",
    CSCSV_ADDR = "Address",
    CSCSV_DOWNLOAD = "Download",
    CSCSV_KEY = "AMap Key:",
    CSCSV_CONFIRM_TITLE = "Download CS",
    CSCSV_CONFIRM = "Are you sure to download CS from AMap?",
    GRID_BASIC = "Basic Information",
    GRID_SB = "Base S:",
    GRID_VB = "Base U:",
    VEH_BASIC = "Basic Information",
    VEH_COUNT = "Vehicle count:",
    VEH_V2GPROP = "V2G prop:",
    VEH_V2GPROP_INFO = "Proportion of vehicles willing to join V2G (0.00~1.00)",
    VEH_SEED = "Seed:",
    VEH_ODSRC = "OD pair source",
    VEH_ODAUTO = "Auto detection",
    VEH_ODTAZ = "By TAZs' types",
    VEH_ODPOLY = "By buildings' contours and types",
    VEH_GEN = "Generate",
    VEH_OMEGA_DESC = "Omega indicates the user's sensitivity to the cost of charging. Bigger Omega means less sensitive.",
    VEH_KREL_DESC = "KRel indicates the user's estimation of the distance. Bigger KRel means the user underestimates the distance.",
    VEH_KSC_DESC = "KSC indicates the SoC threshold for slow charging.",
    VEH_KFC_DESC = "KFC indicates the SoC threshold for fast charging halfway.",
    VEH_KV2G_DESC = "KV2G indicates the SoC threshold of the battery that can be used for V2G.",
    CS_GEN = "Generate a new group of CSs",
    CS_MODE = "Generation Mode",
    CS_USEALL = "All available",
    CS_SELECTED = "Given",
    CS_RANDOM = "Sample N items from available items",
    CS_SRC = "CS Source Edges",
    CS_USEEDGES = "All edges",
    CS_USECSV = "Edges determined by downloaded CS positions",
    CS_USEPOLY = "Edges determined by buildings' contours",
    CS_SLOTS = "Number of slots in each CS",
    CS_SEED = "Random seed",
    CS_PRICEBUY = "Users' buying price",
    CS_PRICESELL = "Users' selling price",
    CS_PB5SEGS = "5 segements random",
    CS_PBFIXED = "Fixed",
    CS_BUSMODE = "Bus Selection Mode",
    CS_BUSUSEALL = "From all available",
    CS_BUSSELECTED = "From given",
    CS_BUSRANDOM = "From N random buses",
    CS_BTN_GEN = "Generate",
    NOT_OPEN = "Not open",
    SAVED = "Saved",
    UNSAVED = "Unsaved",
)

SIM_YES = "YES" #_loc["SIM_YES"]
SIM_NO = "NO" #_loc["SIM_NO"]
    
class CSEditorGUI(Frame):
    def __init__(self, master, generatorFunc, canV2g:bool, file:str="", **kwargs):
        super().__init__(master, **kwargs)
        self.gf = generatorFunc
        if file:
            self.file = file
        else:
            self.file = ""
        
        self.tree = ScrollableTreeView(self, allowSave=True) 
        self.tree['show'] = 'headings'
        if canV2g:
            self.csType = SCS
            self.tree["columns"] = ("Edge", "Slots", "Bus", "x", "y", "Online", "MaxPc", "MaxPd", "PriceBuy", "PriceSell", "PcAlloc", "PdAlloc")
        else:
            self.csType = FCS
            self.tree["columns"] = ("Edge", "Slots", "Bus", "x", "y", "Online", "MaxPc", "PriceBuy", "PcAlloc")
        self.tree.column("Edge", width=120, stretch=NO)
        self.tree.column("Slots", width=90, stretch=NO)
        self.tree.column("Bus", width=80, stretch=NO)
        self.tree.column("x", width=60, stretch=NO)
        self.tree.column("y", width=60, stretch=NO)
        self.tree.column("Online", width=100, stretch=NO)
        self.tree.column("MaxPc", width=130, stretch=NO)
        self.tree.column("PriceBuy", width=120, stretch=YES)
        if canV2g:
            self.tree.column("MaxPd", width=130, stretch=NO)
            self.tree.column("PriceSell", width=120, stretch=YES)
            self.tree.column("PcAlloc", width=80, stretch=NO)
            self.tree.column("PdAlloc", width=80, stretch=NO)
        
        self.tree.heading("Edge", text=_loc["CSE_EDGE"])
        self.tree.heading("Slots", text=_loc["CSE_SLOTS"])
        self.tree.heading("Bus", text=_loc["CSE_BUS"])
        self.tree.heading("x", text=_loc["CSE_X"])
        self.tree.heading("y", text=_loc["CSE_Y"])
        self.tree.heading("Online", text=_loc["CSE_ONLINE"])
        self.tree.heading("MaxPc", text=_loc["CSE_MAXPC"])
        self.tree.heading("PriceBuy", text=_loc["CSE_PRICEBUY"])
        self.tree.heading("PcAlloc", text=_loc["CSE_PCALLOC"])

        self.tree.setColEditMode("Edge", "entry")
        self.tree.setColEditMode("Slots", "spin", spin_from = 0, spin_to = 100)
        self.tree.setColEditMode("Bus", "entry")
        self.tree.setColEditMode("x", "entry")
        self.tree.setColEditMode("y", "entry")
        self.tree.setColEditMode("Online", "rangelist", rangelist_hint=True)
        self.tree.setColEditMode("MaxPc", "spin", spin_from = 0, spin_to = 1000)
        self.tree.setColEditMode("PriceBuy", "segfunc")
        self.tree.setColEditMode("PcAlloc", "combo", combo_values=["Average", "Prioritized"])
        
        if canV2g:
            self.tree.heading("PriceSell", text=_loc["CSE_PRICESELL"])
            self.tree.heading("MaxPd", text=_loc["CSE_MAXPD"])
            self.tree.heading("PdAlloc", text=_loc["CSE_PDALLOC"])
            self.tree.setColEditMode("PriceSell", "segfunc")
            self.tree.setColEditMode("MaxPd", "spin", spin_from = 0, spin_to = 1000)
            self.tree.setColEditMode("PdAlloc", "combo", combo_values=["Average"])
        self.tree.pack(fill="both", expand=True)

        self.panel2 = Frame(self)
        self.btn_find = Button(self.panel2, text=_loc["BTN_FIND"], command=self._on_btn_find_click)
        self.btn_find.pack(fill="x", side='right', anchor='e', expand=False)
        self.entry_find = Entry(self.panel2)
        self.entry_find.pack(fill="x", side='right', anchor='e',expand=False)
        self.lb_cnt = Label(self.panel2, text=_loc["LB_COUNT"].format(0))
        self.lb_cnt.pack(fill="x", side='left', anchor='w', expand=False)
        self.panel2.pack(fill="x")

        self.gens = LabelFrame(self, text=_loc["CS_GEN"])
        self.gens.pack(fill="x", expand=False)

        self.useMode = IntVar(self, 0)
        self.group_use = LabelFrame(self.gens, text=_loc["CS_MODE"])
        self.rb_useAll = Radiobutton(self.group_use, text=_loc["CS_USEALL"], value=0, variable=self.useMode, command=self._useModeChanged)
        self.rb_useAll.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.rb_useSel = Radiobutton(self.group_use, text=_loc["CS_SELECTED"], value=1, variable=self.useMode, command=self._useModeChanged)
        self.rb_useSel.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.entry_sel = Entry(self.group_use, state="disabled")
        self.entry_sel.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.rb_useRandN = Radiobutton(self.group_use, text=_loc["CS_RANDOM"], value=2, variable=self.useMode, command=self._useModeChanged)
        self.rb_useRandN.grid(row=0,column=3,padx=3,pady=3,sticky="w")
        self.entry_randN = Entry(self.group_use, state="disabled")
        self.entry_randN.grid(row=0,column=4,padx=3,pady=3,sticky="w")
        self.group_use.grid(row=2,column=0,padx=3,pady=3,sticky="nesw")

        self.use_cscsv = IntVar(self, 0)
        self.group_src = LabelFrame(self.gens, text=_loc["CS_SRC"])
        self.rb_rnet = Radiobutton(self.group_src, text=_loc["CS_USEEDGES"], value=0, variable=self.use_cscsv)
        self.rb_rnet.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.rb_cscsv = Radiobutton(self.group_src, text=_loc["CS_USECSV"], value=1, variable=self.use_cscsv, state="disabled")
        self.rb_cscsv.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.rb_poly = Radiobutton(self.group_src, text=_loc["CS_USEPOLY"], value=2, variable=self.use_cscsv,state="disabled")
        self.rb_poly.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.group_src.grid(row=1,column=0,padx=3,pady=3,sticky="nesw")

        self.fr = Frame(self.gens)
        self.lb_slots = Label(self.fr, text=_loc["CS_SLOTS"])
        self.lb_slots.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.entry_slots = Entry(self.fr)
        self.entry_slots.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.entry_slots.insert(0, "10")
        self.lb_seed = Label(self.fr, text=_loc["CS_SEED"])
        self.lb_seed.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.entry_seed = Entry(self.fr)
        self.entry_seed.grid(row=0,column=3,padx=3,pady=3,sticky="w")
        self.entry_seed.insert(0, "0")
        self.fr.grid(row=0,column=0,padx=3,pady=3,sticky="nesw")
        
        self.pbuy = IntVar(self, 1)
        self.group_pbuy = LabelFrame(self.gens, text=_loc["CS_PRICEBUY"])
        self.rb_pbuy0 = Radiobutton(self.group_pbuy, text=_loc["CS_PB5SEGS"], value=0, variable=self.pbuy, command=self._pBuyChanged)
        self.rb_pbuy0.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.rb_pbuy1 = Radiobutton(self.group_pbuy, text=_loc["CS_PBFIXED"], value=1, variable=self.pbuy, command=self._pBuyChanged)
        self.rb_pbuy1.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.entry_pbuy = Entry(self.group_pbuy)
        self.entry_pbuy.insert(0, "1.0")
        self.entry_pbuy.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.group_pbuy.grid(row=3,column=0,padx=3,pady=3,sticky="nesw")

        self.psell = IntVar(self, 1)
        self.group_psell = LabelFrame(self.gens, text=_loc["CS_PRICESELL"])
        self.rb_psell0 = Radiobutton(self.group_psell, text=_loc["CS_PB5SEGS"], value=0, variable=self.psell, command=self._pSellChanged)
        self.rb_psell0.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.rb_psell1 = Radiobutton(self.group_psell, text=_loc["CS_PBFIXED"], value=1, variable=self.psell, command=self._pSellChanged)
        self.rb_psell1.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.entry_psell = Entry(self.group_psell)
        self.entry_psell.insert(0, "1.5")
        self.entry_psell.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.group_psell.grid(row=4,column=0,padx=3,pady=3,sticky="nesw")

        self.busMode = IntVar(self, 0)
        self.group_bus = LabelFrame(self.gens, text=_loc["CS_BUSMODE"])
        self.rb_busAll = Radiobutton(self.group_bus, text=_loc["CS_BUSUSEALL"], value=0, variable=self.busMode, command=self._busModeChanged)
        self.rb_busAll.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.rb_busSel = Radiobutton(self.group_bus, text=_loc["CS_BUSSELECTED"], value=1, variable=self.busMode, command=self._busModeChanged)
        self.rb_busSel.grid(row=0,column=1,padx=3,pady=3,sticky="w")
        self.entry_bussel = Entry(self.group_bus, state="disabled")
        self.entry_bussel.grid(row=0,column=2,padx=3,pady=3,sticky="w")
        self.rb_busRandN = Radiobutton(self.group_bus, text=_loc["CS_BUSRANDOM"], value=2, variable=self.busMode, command=self._busModeChanged)
        self.rb_busRandN.grid(row=0,column=3,padx=3,pady=3,sticky="w")
        self.entry_busrandN = Entry(self.group_bus, state="disabled")
        self.entry_busrandN.grid(row=0,column=4,padx=3,pady=3,sticky="w")
        self.group_bus.grid(row=5,column=0,padx=3,pady=3,sticky="nesw")

        self.btn_regen = Button(self.gens, text=_loc["CS_BTN_GEN"], command=self.generate)
        self.btn_regen.grid(row=6,column=0,padx=3,pady=3,sticky="w")
        self.tree.setOnSave(self.save())

        self.cslist:list[CS] = []
    
    @property
    def saved(self):
        return self.tree.saved
    
    def save(self):
        def mkFunc(s:str):
            try:
                return ConstFunc(float(s))
            except:
                return SegFunc(eval(s))
            
        def _save(data:list[tuple]):
            if not self.file: return False
            assert len(self.cslist) == len(data)
            with open(self.file, "w") as f:
                f.write(f"<?xml version='1.0' encoding='utf-8'?>\n<root>\n")
                if self.csType == FCS:
                    for i, d in enumerate(data):
                        assert len(d) == 9
                        name, slots, bus, x, y, ol, maxpc, pbuy, pcalloc = d
                        c = self.cslist[i]
                        c._name = name
                        c._slots = slots
                        c._node = bus
                        c._x = float(x)
                        c._y = float(y)
                        c._pc_lim1 = float(maxpc) / 3600
                        if ol == ALWAYS_ONLINE: ol = "[]"
                        c._offline = RangeList(eval(ol))
                        c._pbuy = OverrideFunc(mkFunc(pbuy))
                        f.write(c.to_xml())
                        f.write("\n")
                else:
                    for i, d in enumerate(data):
                        assert len(d) == 12
                        name, slots, bus, x, y, ol, maxpc, maxpd, pbuy, psell, pcalloc, pdalloc = d
                        c = self.cslist[i]
                        c._name = name
                        c._slots = slots
                        c._node = bus
                        c._x = float(x)
                        c._y = float(y)
                        c._pc_lim1 = float(maxpc) / 3600
                        c._pd_lim1 = float(maxpd) / 3600
                        if ol == ALWAYS_ONLINE: ol = "[]"
                        c._offline = RangeList(eval(ol))
                        c._pbuy = OverrideFunc(mkFunc(pbuy))
                        c._psell = OverrideFunc(mkFunc(psell))
                        c._pc_alloc_str = pcalloc
                        c._pd_alloc_str = pdalloc
                        f.write(c.to_xml())
                        f.write("\n")
                f.write("</root>")
            return True
        return _save

    def FindCS(self, edge:str):
        for item in self.tree.get_children():
            if self.tree.item(item, 'values')[0] == edge:
                self.tree.tree.selection_set(item)
                self.tree.tree.focus(item)
                self.tree.tree.see(item)
                break
    
    def _on_btn_find_click(self):
        self.FindCS(self.entry_find.get())
    
    def setPoly(self, val:bool):
        if not val:
            self.rb_poly.configure(state="disabled")
            if self.use_cscsv.get() == 2:
                self.use_cscsv.set(0)
        else:
            self.rb_poly.configure(state="normal")
    
    def setCSCSV(self, val:bool):
        if not val:
            self.rb_cscsv.configure(state="disabled")
            if self.use_cscsv.get() == 1:
                self.use_cscsv.set(0)
        else:
            self.rb_cscsv.configure(state="normal")

    def _pBuyChanged(self):
        v = self.pbuy.get()
        if v == 0:
            self.entry_pbuy.config(state="disabled")
        else:
            self.entry_pbuy.config(state="normal")
    
    def _pSellChanged(self):
        v = self.psell.get()
        if v == 0:
            self.entry_psell.config(state="disabled")
        else:
            self.entry_psell.config(state="normal")
    
    def _useModeChanged(self):
        v = self.useMode.get()
        if v == 0:
            self.entry_sel.config(state="disabled")
            self.entry_randN.config(state="disabled")
        elif v == 1:
            self.entry_sel.config(state="normal")
            self.entry_randN.config(state="disabled")
        else:
            self.entry_sel.config(state="disabled")
            self.entry_randN.config(state="normal")
    
    def _busModeChanged(self):
        v = self.busMode.get()
        if v == 0:
            self.entry_bussel.config(state="disabled")
            self.entry_busrandN.config(state="disabled")
        elif v == 1:
            self.entry_bussel.config(state="normal")
            self.entry_busrandN.config(state="disabled")
        else:
            self.entry_bussel.config(state="disabled")
            self.entry_busrandN.config(state="normal")

    def generate(self):
        try:
            seed = int(self.entry_seed.get())
        except:
            showerr("Invalid seed")
            return
        try:
            slots = int(self.entry_slots.get())
        except:
            showerr("Invalid slots")
            return
        mode = "fcs" if self.csType == FCS else "scs"
        if self.useMode.get() == 0:
            cs = ListSelection.ALL
            csCount = -1
            givenCS = []
        elif self.useMode.get() == 1:
            cs = ListSelection.GIVEN
            csCount = -1
            try:
                givenCS = self.entry_sel.get().split(',')
            except:
                showerr("Invalid given CS")
                return
            if len(givenCS) == 0 or len(givenCS) == 1 and givenCS[0] == "":
                showerr("No given CS")
                return
        else:
            cs = ListSelection.RANDOM
            try:
                csCount = int(self.entry_randN.get())
            except:
                showerr("Invalid random N of CS")
                return
            givenCS = []
        if self.busMode.get() == 0:
            bus = ListSelection.ALL
            busCount = -1
            givenbus = []
        elif self.busMode.get() == 1:
            bus = ListSelection.GIVEN
            busCount = -1
            try:
                givenbus = self.entry_bussel.get().split(',')
            except:
                showerr("Invalid given bus")
                return
            if len(givenbus) == 0 or len(givenbus) == 1 and givenbus[0] == "":
                showerr("No given bus")
                return
        else:
            bus = ListSelection.RANDOM
            try:
                busCount = int(self.entry_randN.get())
            except:
                showerr("Invalid random N of bus")
                return
            givenbus = []
        
        if self.pbuy.get() == 0:
            pbuyM = PricingMethod.RANDOM
            pbuy = 1.0
        else:
            pbuyM = PricingMethod.FIXED
            try:
                pbuy = float(self.entry_pbuy.get())
            except:
                showerr("Invalid price buy")
                return
        if self.csType == FCS:
            if self.psell.get() == 0:
                psellM = PricingMethod.RANDOM
                psell = 0
            else:
                psellM = PricingMethod.FIXED
                try:
                    psell = float(self.entry_psell.get())
                except:
                    showerr("Invalid price sell")
                    return
        else:
            psellM = PricingMethod.FIXED
            psell = 0
        self.gf(self.use_cscsv.get(), seed = seed, mode = mode, slots = slots,
                bus = bus, busCount = busCount, givenBus = givenbus,
                cs = cs, csCount = csCount, givenCS = givenCS, 
                priceBuyMethod = pbuyM, priceBuy = pbuy, priceSellMethod = psellM, 
                priceSell = psell, hasSell = self.csType == SCS)

    def __update_gui(self):
        cnt = 0
        LIMIT = 50
        try:
            while cnt < LIMIT:
                cnt += 1
                t, x = self.__q.get_nowait()
                if t == 'v':
                    self.tree.insert("", "end", values=x)
                elif t == 'a':
                    x and x()
        except queue.Empty:
            pass
        if not self.__q_closed or cnt >= LIMIT:
            self.tree.after(10, self.__update_gui)
    
    def load(self, file:str, async_:bool = False, after:OAfter=None):
        if async_:
            self.__q = Queue()
            self.__q_closed = False
            threading.Thread(target=self.__load, args=(file, True, after), daemon=True).start()
            self.tree.after(10, self.__update_gui)
        else:
            self.__load(file, False, after)
    
    def clear(self):
        self.tree.clear()
        self.lb_cnt.config(text=_loc["LB_COUNT"].format(0))
    
    def __load(self, file:str, async_:bool=False, after:OAfter=None):
        try:
            self.cslist = LoadCSList(file, self.csType)
        except Exception as e:
            showerr(f"Error loading {file}: {e}")
            return
        self.file = file
        self.tree.clear()
        self.lb_cnt.config(text=_loc["LB_COUNT"].format(len(self.cslist)))
        if self.csType == FCS:
            for cs in self.cslist:
                ol = str(cs._offline) if len(cs._offline)>0 else ALWAYS_ONLINE
                v = (cs.name, cs.slots, cs.node, cs._x, cs._y, ol, cs._pc_lim1 * 3600, cs.pbuy, cs._pc_alloc_str)
                if async_:
                    self.__q.put(('v',v))
                else:
                    self.tree.insert("", "end", values=v)
        else:
            for cs in self.cslist:
                assert isinstance(cs, SCS)
                ol = str(cs._offline) if len(cs._offline)>0 else ALWAYS_ONLINE
                v = (cs.name, cs.slots, cs.node, cs._x, cs._y, ol, cs._pc_lim1 * 3600, cs._pd_lim1 * 3600, 
                            cs.pbuy, cs.psell, cs._pc_alloc_str, cs._pd_alloc_str)
                if async_:
                    self.__q.put(('v',v))
                else:
                    self.tree.insert("", "end", values=v)
        if async_:
            self.__q.put(('a', after))
            self.__q_closed = False
        else:
            after and after()
    
    
class CSCSVEditor(Frame):
    def __init__(self, master, down_worker, file:str="", **kwargs):
        super().__init__(master, **kwargs)
        if file:
            self.file = file
        else:
            self.file = ""
        self.down_wk = down_worker
        self.tree = ScrollableTreeView(self) 
        self.tree['show'] = 'headings'
        self.tree["columns"] = ("ID", "Address", "X", "Y")
        self.tree.column("ID", width=120, stretch=NO)
        self.tree.column("X", width=100, stretch=NO)
        self.tree.column("Y", width=100, stretch=NO)
        self.tree.column("Address", width=180, stretch=YES)
        
        self.tree.heading("ID", text=_loc["CSCSV_ID"])
        self.tree.heading("X", text=_loc["CSCSV_X"])
        self.tree.heading("Y", text=_loc["CSCSV_Y"])
        self.tree.heading("Address", text=_loc["CSCSV_ADDR"])
        self.tree.pack(fill="both", expand=True)

        self.lb_cnt = Label(self, text=_loc["LB_COUNT"].format(0))
        self.lb_cnt.pack(fill="x", expand=False)

        self.panel = Frame(self)
        self.panel.pack(fill="x", expand=False)
        self.btn_down = Button(self.panel, text=_loc["CSCSV_DOWNLOAD"], command=self.down)
        self.btn_down.grid(row=0,column=0,padx=3,pady=3,sticky="w")
        self.lb_amapkey = Label(self.panel, text=_loc["CSCSV_KEY"])
        self.lb_amapkey.grid(row=0, column=1, padx=3, pady=3, sticky="w")
        self.entry_amapkey = Entry(self.panel, width=50)
        self.entry_amapkey.grid(row=0, column=2, columnspan=2, padx=3, pady=3, sticky="w")

        if Path("amap_key.txt").exists():
            with open("amap_key.txt", "r") as f:
                self.entry_amapkey.insert(0, f.read().strip())
        
    def down(self):
        if MB.askyesno(_loc["CSCSV_CONFIRM_TITLE"], _loc["CSCSV_CONFIRM"]):
            self.down_wk()
    
    def __load(self, file:str, async_:bool=False, after:OAfter=None):
        try:
            with open(file, "r") as f:
                lines = f.readlines()
        except Exception as e:
            showerr(f"Error loading {file}: {e}")
            return
        self.file = file
        self.lb_cnt.config(text=_loc["LB_COUNT"].format(len(lines) - 1))
        self.tree.clear()
        for cs in lines[1:]:
            vals = cs.strip().split(',')
            if async_:
                self.__q.put(('v', tuple(vals)))
            else:
                self.tree.insert("", "end", values=tuple(vals))
        if async_:
            self.__q.put(('a', after))
            self.__q_closed = True
        else:
            after and after()

    def __update_gui(self):
        LIMIT = 50
        try:
            cnt = 0
            while cnt < LIMIT:
                cnt += 1
                t, x = self.__q.get_nowait()
                if t == 'v':
                    self.tree.insert("", "end", values=x)
                elif t == 'a':
                    x and x()
        except queue.Empty:
            pass
        if not self.__q_closed or cnt >= LIMIT:
            self.tree.after(10, self.__update_gui)

    def load(self, file:str, async_:bool, after:OAfter=None):
        if async_:
            self.__q = Queue()
            self.__q_closed = False
            threading.Thread(target=self.__load, args=(file, True, after), daemon=True).start()
            self.tree.after(10, self.__update_gui)
        else:
            self.__load(file, False, after)
    
    def clear(self):
        self.lb_cnt.config(text=_loc["LB_COUNT"].format(0))
        self.tree.clear()


class LoadingBox(Toplevel):
    def __init__(self, items:list[str], **kwargs):
        super().__init__(None, **kwargs)
        self.title("Loading...")
        self.geometry("400x300")
        self.cks:list[Label]=[]
        self.dkt:dict[str,int]={}
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        for i, t in enumerate(items):
            Label(self, text=t).grid(column=0,row=i)
            self.cks.append(Label(self, text="..."))
            self.cks[-1].grid(column=1,row=i)
            self.dkt[t]=i
            self.rowconfigure(i, weight=1)
    
    def setText(self, itm:str, val:str):
        self.cks[self.dkt[itm]].configure(text=val)
        for x in self.cks:
            if x['text'] != _loc['DONE']: break
        else:
            self.destroy()
    

class MainBox(Tk):
    @staticmethod
    def setLang(lang_code:str):
        def _f():
            _loc.DefaultLanguage = lang_code
            Lang.load(lang_code)
            Lang.save_lang_code(lang_code == "<auto>")
            MB.showinfo(_loc["MB_INFO"],_loc["LANG_RESTART"])
        return _f
    
    def _OnPDNEnabledSet(self):
        def _setSimStat(itm:tuple[Any,...], v:str):
            if itm[0] != "pdn": return
            t = "enabled" if v == SIM_YES else "disabled"
            self.sim_cb_line.configure(state=t)
            self.sim_cb_bus.configure(state=t)
            self.sim_cb_gen.configure(state=t)
            tv = v == SIM_YES
            self.sim_sta_line.set(tv)
            self.sim_sta_bus.set(tv)
            self.sim_sta_gen.set(tv)
        return _setSimStat
    
    def __init__(self):
        super().__init__()
        self._Q = Queue()
        self.folder:str = ""
        self.state:Optional[FileDetectResult] = None
        self.tg:Optional[TrafficGenerator] = None
        self._win()

        self.menu = Menu(self)
        self.menuFile = Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label=_loc["MENU_PROJ"], menu=self.menuFile)
        self.menuFile.add_command(label=_loc["MENU_OPEN"], command=self.openFolder, accelerator='Ctrl+O')
        self.bind("<Control-o>", lambda e: self.openFolder())
        self.menuFile.add_command(label=_loc["MENU_SAVEALL"], command=self.save, accelerator="Ctrl+S")
        self.bind("<Control-s>", lambda e: self.save())
        self.menuFile.add_separator()
        self.menuFile.add_command(label=_loc["MENU_EXIT"], command=self.onDestroy, accelerator='Ctrl+Q')
        self.bind("<Control-q>", lambda e: self.onDestroy())
        self.menuLang = Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label=_loc["MENU_LANG"], menu=self.menuLang)
        self.menuLang.add_command(label=_loc["MENU_LANG_AUTO"], command=self.setLang("<auto>"))
        self.menuLang.add_command(label=_loc["MENU_LANG_EN"], command=self.setLang("en"))
        self.menuLang.add_command(label=_loc["MENU_LANG_ZHCN"], command=self.setLang("zh_CN"))
        self.config(menu=self.menu)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.panel_info = Frame(self, borderwidth=1, relief="solid")
        self.panel_info.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")

        self.lb_infotitle = Label(self.panel_info, text = _loc["BAR_PROJINFO"], background="white")
        self.lb_infotitle.grid(row=0, column=0, columnspan=2, padx=3, pady=3, sticky="nsew")

        self.lb_fcs_indicatif = Label(self.panel_info, text = _loc["BAR_FCS"])
        self.lb_fcs_indicatif.grid(row=1, column=0, padx=3, pady=3)
        self.lb_fcs = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_fcs.grid(row=1, column=1, padx=3, pady=3)

        self.lb_scs_indicatif = Label(self.panel_info, text = _loc["BAR_SCS"])
        self.lb_scs_indicatif.grid(row=2, column=0, padx=3, pady=3)
        self.lb_scs = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_scs.grid(row=2, column=1, padx=3, pady=3)

        self.lb_grid_indicatif = Label(self.panel_info, text = _loc["BAR_GRID"])
        self.lb_grid_indicatif.grid(row=3, column=0, padx=3, pady=3)
        self.lb_grid = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_grid.grid(row=3, column=1, padx=3, pady=3)

        self.lb_net_indicatif = Label(self.panel_info, text = _loc["BAR_RNET"])
        self.lb_net_indicatif.grid(row=4, column=0, padx=3, pady=3)
        self.lb_net = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_net.grid(row=4, column=1, padx=3, pady=3)

        self.lb_veh_indicatif = Label(self.panel_info, text = _loc["BAR_VEH"])
        self.lb_veh_indicatif.grid(row=5, column=0, padx=3, pady=3)
        self.lb_veh = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_veh.grid(row=5, column=1, padx=3, pady=3)

        self.lb_plg_indicatif = Label(self.panel_info, text = _loc["BAR_PLG"])
        self.lb_plg_indicatif.grid(row=6, column=0, padx=3, pady=3)
        self.lb_plg = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_plg.grid(row=6, column=1, padx=3, pady=3)

        self.lb_cfg_indicatif = Label(self.panel_info, text = _loc["BAR_SUMO"])
        self.lb_cfg_indicatif.grid(row=7, column=0, padx=3, pady=3)
        self.lb_cfg = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_cfg.grid(row=7, column=1, padx=3, pady=3)

        self.lb_taz_indicatif = Label(self.panel_info, text = _loc["BAR_TAZ"])
        self.lb_taz_indicatif.grid(row=8, column=0, padx=3, pady=3)
        self.lb_taz = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_taz.grid(row=8, column=1, padx=3, pady=3)

        self.lb_py_indicatif = Label(self.panel_info, text = _loc["BAR_ADDON"])
        self.lb_py_indicatif.grid(row=9, column=0, padx=3, pady=3)
        self.lb_py = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_py.grid(row=9, column=1, padx=3, pady=3)

        self.lb_taz_type_indicatif = Label(self.panel_info, text = _loc["BAR_TAZTYPE"])
        self.lb_taz_type_indicatif.grid(row=10, column=0, padx=3, pady=3)
        self.lb_taz_type = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_taz_type.grid(row=10, column=1, padx=3, pady=3)

        self.lb_osm_indicatif = Label(self.panel_info, text = _loc["BAR_OSM"])
        self.lb_osm_indicatif.grid(row=11, column=0, padx=3, pady=3)
        self.lb_osm = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_osm.grid(row=11, column=1, padx=3, pady=3)

        self.lb_poly_indicatif = Label(self.panel_info, text = _loc["BAR_POLY"])
        self.lb_poly_indicatif.grid(row=12, column=0, padx=3, pady=3)
        self.lb_poly = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_poly.grid(row=12, column=1, padx=3, pady=3)

        self.lb_cscsv_indicatif = Label(self.panel_info, text = _loc["BAR_CSCSV"])
        self.lb_cscsv_indicatif.grid(row=13, column=0, padx=3, pady=3)
        self.lb_cscsv = Label(self.panel_info, text = _loc["BAR_NONE"])
        self.lb_cscsv.grid(row=13, column=1, padx=3, pady=3)

        self.tabs = Notebook(self)
        self.tabs.grid(row=0, column=1, padx=3, pady=3, sticky="nsew")

        self.tab_sim = Frame(self.tabs)
        self.sim_time = LabelFrame(self.tab_sim, text=_loc["SIM_BASIC"])
        self.sim_time.pack(fill="x", expand=False)
        self.lb_start = Label(self.sim_time, text=_loc["SIM_BEGT"])
        self.lb_start.grid(row=0, column=0, padx=3, pady=3, sticky="w")
        self.entry_start = Entry(self.sim_time)
        self.entry_start.insert(0, "0")
        self.entry_start.grid(row=0, column=1, padx=3, pady=3, sticky="w")
        self.lb_end = Label(self.sim_time, text=_loc["SIM_ENDT"])
        self.lb_end.grid(row=1, column=0, padx=3, pady=3, sticky="w")
        self.entry_end = Entry(self.sim_time)
        self.entry_end.insert(0, "172800")
        self.entry_end.grid(row=1, column=1, padx=3, pady=3, sticky="w")
        self.lb_step = Label(self.sim_time, text=_loc["SIM_STEP"])
        self.lb_step.grid(row=2, column=0, padx=3, pady=3, sticky="w")
        self.entry_step = Entry(self.sim_time)
        self.entry_step.insert(0, "10")
        self.entry_step.grid(row=2, column=1, padx=3, pady=3, sticky="w")
        self.lb_seed = Label(self.sim_time, text=_loc["SIM_SEED"])
        self.lb_seed.grid(row=3, column=0, padx=3, pady=3, sticky="w")
        self.entry_seed = Entry(self.sim_time)
        self.entry_seed.insert(0, "0")
        self.entry_seed.grid(row=3, column=1, padx=3, pady=3, sticky="w")
        self.sim_load_last_state = BooleanVar(self, False)
        self.sim_cb_load_last_state = Checkbutton(self.sim_time, text=_loc["SIM_LOAD_LAST_STATE"], variable=self.sim_load_last_state)
        self.sim_cb_load_last_state.grid(row=4, column=0, padx=3, pady=3, sticky="w", columnspan=2)
        self.sim_save_on_abort = BooleanVar(self, False)
        self.sim_cb_save_on_abort = Checkbutton(self.sim_time, text=_loc["SIM_SAVE_ON_ABORT"], variable=self.sim_save_on_abort)
        self.sim_cb_save_on_abort.grid(row=5, column=0, padx=3, pady=3, sticky="w", columnspan=2)
        self.sim_save_on_finish = BooleanVar(self, False)
        self.sim_cb_save_on_finish = Checkbutton(self.sim_time, text=_loc["SIM_SAVE_ON_FINISH"], variable=self.sim_save_on_finish)
        self.sim_cb_save_on_finish.grid(row=6, column=0, padx=3, pady=3, sticky="w", columnspan=2)

        self.sim_plugins = LabelFrame(self.tab_sim, text=_loc["SIM_PLUGIN"])
        self.sim_plglist = ScrollableTreeView(self.sim_plugins, True)
        self.sim_plglist['show'] = 'headings'
        self.sim_plglist["columns"] = ("Name", "Interval", "Enabled", "Online", "Extra")
        self.sim_plglist.column("Name", width=120, stretch=NO)
        self.sim_plglist.column("Interval", width=100, stretch=NO)
        self.sim_plglist.column("Enabled", width=100, stretch=NO)
        self.sim_plglist.column("Online", width=200, stretch=NO)
        self.sim_plglist.column("Extra", width=200, stretch=YES)
        self.sim_plglist.heading("Name", text=_loc["SIM_PLGNAME"])
        self.sim_plglist.heading("Interval", text=_loc["SIM_EXEINTV"])
        self.sim_plglist.heading("Enabled", text=_loc["SIM_ENABLED"])
        self.sim_plglist.heading("Online", text=_loc["SIM_PLGOL"])
        self.sim_plglist.heading("Extra", text=_loc["SIM_PLGPROP"])
        self.sim_plglist.setColEditMode("Interval", "spin", spin_from=1, spin_to=86400)
        self.sim_plglist.setColEditMode("Enabled", "combo", combo_values=[SIM_YES,SIM_NO],post_func=self._OnPDNEnabledSet())
        self.sim_plglist.setColEditMode("Online", "rangelist", rangelist_hint = True)
        self.sim_plglist.setColEditMode("Extra", "prop")
        self.sim_plglist.pack(fill="both", expand=True)
        self.sim_plugins.pack(fill="x", expand=False)
        self.sim_plglist.setOnSave(self.savePlugins())

        self.sim_statistic = LabelFrame(self.tab_sim, text=_loc["SIM_STAT"])
        self.sim_statistic.pack(fill="x", expand=False)
        self.sim_sta_fcs = BooleanVar(self, True)
        self.sim_cb_fcs = Checkbutton(self.sim_statistic, text=_loc["SIM_FCS"], variable=self.sim_sta_fcs)
        self.sim_cb_fcs.grid(row=0, column=0, padx=3, pady=3, sticky="w")
        self.sim_sta_scs = BooleanVar(self, True)
        self.sim_cb_scs = Checkbutton(self.sim_statistic, text=_loc["SIM_SCS"], variable=self.sim_sta_scs)
        self.sim_cb_scs.grid(row=0, column=1, padx=3, pady=3, sticky="w")
        self.sim_sta_ev = BooleanVar(self, False)
        self.sim_cb_ev = Checkbutton(self.sim_statistic, text=_loc["SIM_VEH"], variable=self.sim_sta_ev)
        self.sim_cb_ev.grid(row=0, column=2, padx=3, pady=3, sticky="w")
        self.sim_sta_gen = BooleanVar(self, True)
        self.sim_cb_gen = Checkbutton(self.sim_statistic, text=_loc["SIM_GEN"], variable=self.sim_sta_gen)
        self.sim_cb_gen.grid(row=0, column=3, padx=3, pady=3, sticky="w")
        self.sim_sta_bus = BooleanVar(self, True)
        self.sim_cb_bus = Checkbutton(self.sim_statistic, text=_loc["SIM_BUS"], variable=self.sim_sta_bus)
        self.sim_cb_bus.grid(row=0, column=4, padx=3, pady=3, sticky="w")
        self.sim_sta_line = BooleanVar(self, True)
        self.sim_cb_line = Checkbutton(self.sim_statistic, text=_loc["SIM_LINE"], variable=self.sim_sta_line)
        self.sim_cb_line.grid(row=0, column=5, padx=3, pady=3, sticky="w")

        self.sim_btn = Button(self.tab_sim, text=_loc["SIM_START"], command=self.simulate)
        self.sim_btn.pack(anchor="w", padx=3, pady=3)
        self.tabs.add(self.tab_sim, text=_loc["TAB_SIM"])

        self.tab_CsCsv = Frame(self.tabs)
        self.CsCsv_editor = CSCSVEditor(self.tab_CsCsv, self.CSCSVDownloadWorker)
        self.CsCsv_editor.pack(fill="both", expand=True)
        self.tabs.add(self.tab_CsCsv, text=_loc["TAB_CSCSV"])

        self.tab_FCS = Frame(self.tabs)
        self.FCS_editor = CSEditorGUI(self.tab_FCS, self.generateCS, False)
        self.FCS_editor.pack(fill="both", expand=True)
        self.tabs.add(self.tab_FCS, text=_loc["TAB_FCS"])

        self.tab_SCS = Frame(self.tabs)
        self.SCS_editor = CSEditorGUI(self.tab_SCS, self.generateCS, True)
        self.SCS_editor.pack(fill="both", expand=True)
        self.tabs.add(self.tab_SCS, text=_loc["TAB_SCS"])

        self.tab_Net = Frame(self.tabs)
        self.cv_net = NetworkPanel(self.tab_Net)
        self.cv_net.pack(fill=BOTH, expand=True)
        self.panel_net = LabelFrame(self.tab_Net, text=_loc["RNET_TITLE"])
        self.lb_gridsave = Label(self.panel_net, text=_loc["NOT_OPEN"])
        self.lb_gridsave.pack(side='left',padx=3,pady=3, anchor='w')
        def on_saved_changed(saved:bool):
            if saved:
                self.lb_gridsave.config(text=_loc["SAVED"],foreground="green")
            else:
                self.lb_gridsave.config(text=_loc["UNSAVED"],foreground="red")
        self.cv_net.save_callback = on_saved_changed
        self.btn_savegrid = Button(self.panel_net, text=_loc["SAVE_GRID"], command=self.saveGrid)
        self.btn_savegrid.pack(side='left',padx=3,pady=3, anchor='w')
        self.lb_puvalues = Label(self.panel_net, text=_loc["PU_VALS"].format('Null','Null'))
        self.lb_puvalues.pack(side='left',padx=3,pady=3, anchor='w')
        self.btn_draw = Button(self.panel_net, text=_loc["RNET_DRAW"], command=self.draw)
        self.btn_draw.pack(side="right", padx=3, pady=3, anchor="e")
        self.entry_locedges = Entry(self.panel_net)
        self.entry_locedges.pack(side="right", padx=3, pady=3, anchor="e")
        self.lb_locedges = Label(self.panel_net, text=_loc["RNET_EDGES"])
        self.lb_locedges.pack(side="right", padx=3, pady=3, anchor="e")
        
        self.panel_net.pack(fill="x", expand=False, anchor="s")
        self.tabs.add(self.tab_Net, text=_loc["TAB_RNET"])

        self.tab_Veh = Frame(self.tabs)
        self.fr_veh_basic = LabelFrame(self.tab_Veh,text=_loc["VEH_BASIC"])
        self.fr_veh_basic.pack(fill="x", expand=False)
        self.lb_carcnt = Label(self.fr_veh_basic, text=_loc["VEH_COUNT"])
        self.lb_carcnt.grid(row=0, column=0, padx=3, pady=3, sticky="w")
        self.entry_carcnt = Entry(self.fr_veh_basic)
        self.entry_carcnt.insert(0, "10000")
        self.entry_carcnt.grid(row=0, column=1, padx=3, pady=3, sticky="w")
        self.lb_v2gprop = Label(self.fr_veh_basic, text=_loc["VEH_V2GPROP"])
        self.lb_v2gprop.grid(row=1, column=0, padx=3, pady=3, sticky="w")
        self.entry_v2gprop = Entry(self.fr_veh_basic)
        self.entry_v2gprop.insert(0, "1.00")
        self.entry_v2gprop.grid(row=1, column=1, padx=3, pady=3, sticky="w")
        self.lb_v2gprop_info = Label(self.fr_veh_basic, text=_loc["VEH_V2GPROP_INFO"])
        self.lb_v2gprop_info.grid(row=1, column=2, padx=3, pady=3, sticky="w")
        self.lb_carseed = Label(self.fr_veh_basic, text=_loc["VEH_SEED"])
        self.lb_carseed.grid(row=2, column=0, padx=3, pady=3, sticky="w")
        self.entry_carseed = Entry(self.fr_veh_basic)
        self.entry_carseed.insert(0, "0")
        self.entry_carseed.grid(row=2, column=1, padx=3, pady=3, sticky="w")

        self.veh_pars = PropertyPanel(self.tab_Veh, {
            "Omega":repr(PDUniform(5.0, 10.0)),
            "KRel":repr(PDUniform(1.0, 1.2)),
            "KSC":repr(PDUniform(0.4, 0.6)),
            "KFC":repr(PDUniform(0.2, 0.25)),
            "KV2G":repr(PDUniform(0.65, 0.75)),
        }, default_edit_mode=EditMode.PDFUNC, desc = {
            "Omega": _loc["VEH_OMEGA_DESC"],
            "KRel": _loc["VEH_KREL_DESC"],
            "KSC": _loc["VEH_KSC_DESC"],
            "KFC": _loc["VEH_KFC_DESC"],
            "KV2G": _loc["VEH_KV2G_DESC"],
        })
        self.veh_pars.pack(fill="x", expand=False, pady=10)

        self.veh_gen_src = IntVar(self, 0)
        self.fr_veh_src = LabelFrame(self.tab_Veh,text=_loc["VEH_ODSRC"])
        self.fr_veh_src.pack(fill="x", expand=False)
        self.rb_veh_src0 = Radiobutton(self.fr_veh_src, text=_loc["VEH_ODAUTO"], value=0, variable=self.veh_gen_src)
        self.rb_veh_src0.grid(row=0, column=0, padx=3, pady=3, sticky="w")
        self.rb_veh_src1 = Radiobutton(self.fr_veh_src, text=_loc["VEH_ODTAZ"], value=1, variable=self.veh_gen_src)
        self.rb_veh_src1.grid(row=1, column=0, padx=3, pady=3, sticky="w")
        self.rb_veh_src2 = Radiobutton(self.fr_veh_src, text=_loc["VEH_ODPOLY"], value=2, variable=self.veh_gen_src)
        self.rb_veh_src2.grid(row=2, column=0, padx=3, pady=3, sticky="w")
        self.btn_genveh = Button(self.tab_Veh, text=_loc["VEH_GEN"], command=self.generateVeh)
        self.btn_genveh.pack(anchor="w")
        self.tabs.add(self.tab_Veh, text=_loc["TAB_VEH"])

        self.sbar = Label(self, text=_loc["STA_READY"], anchor="w")
        self.sbar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.protocol("WM_DELETE_WINDOW", self.onDestroy)
        self.after(100, self._loop)
    
    def veh_par_edit(self, var:StringVar):
        def _f():
            e = PDFuncEditor(var)
            e.wait_window()
        return _f

    @property
    def saved(self):
        return self.sim_plglist.saved and self.FCS_editor.saved and self.SCS_editor.saved and self.cv_net.saved
    
    def save(self):
        if not self.sim_plglist.saved: self.sim_plglist.save()
        if not self.FCS_editor.saved: self.FCS_editor.save()
        if not self.SCS_editor.saved: self.SCS_editor.save()
        if not self.cv_net.saved: self.saveGrid()
    
    def saveGrid(self):
        defpath = self.folder+"/"+DEFAULT_GRID_NAME
        if self.state.grid:
            path = self.state.grid
            os.remove(path)
            if not path.lower().endswith(".xml"): path = defpath
        else:
            path = defpath
        self.cv_net.saveGrid(path)
        
    def onDestroy(self):
        if not self.saved:
            ret = MB.askyesnocancel(_loc["MB_INFO"], _loc["MB_EXIT_SAVE"])
            if ret is None: return
            if ret: self.save()
        self.destroy()

    def simulate(self):
        if not self.__checkFolderOpened():
            return
        try:
            start = int(self.entry_start.get())
            end = int(self.entry_end.get())
            step = int(self.entry_step.get())
            seed = int(self.entry_seed.get())
        except:
            showerr("Invalid time")
            return
        if not self.state:
            showerr("No project loaded")
            return
        if "scs" not in self.state:
            showerr("No SCS loaded")
            return
        if "fcs" not in self.state:
            showerr("No FCS loaded")
            return
        if "veh" not in self.state:
            showerr("No vehicles loaded")
            return
        logs = []
        if self.sim_sta_fcs.get():
            logs.append("fcs")
        if self.sim_sta_scs.get():
            logs.append("scs")
        if self.sim_sta_ev.get():
            logs.append("ev")
        if self.sim_sta_gen.get():
            logs.append("gen")
        if self.sim_sta_bus.get():
            logs.append("bus")
        if self.sim_sta_line.get():
            logs.append("line")
        if not logs:
            showerr("No statistics selected")
            return
        if not self.saved:
            if not MB.askyesno(_loc["MB_INFO"],_loc["MB_SAVE_AND_SIM"]): return
            self.save()

        #Check SUMOCFG
        if not self.state.cfg:
            showerr("No SUMO config file detected")
            return
        cflag = False
        tr = ET.ElementTree(file = self.state.cfg)
        cfg = tr.getroot()
        node_report = cfg.find("report")
        route_file_name = ""
        if node_report is not None:
            cfg.remove(node_report)
            cflag = True
        node_routing = cfg.find("routing")
        if node_routing is not None:
            cfg.remove(node_routing)
            cflag = True
        node_input = cfg.find("input")
        if node_input is not None:
            node_rf = node_input.find("route-files")
            if node_rf is not None:
                route_file_name = node_rf.get("value")
                node_input.remove(node_rf)
                cflag = True
        if cflag:
            if MB.askyesno(_loc["MB_INFO"],_loc["MB_CFG_MODIFY"]):
                tr.write(self.state.cfg)
                route_path = Path(self.state.cfg).absolute().parent / route_file_name
                if route_path.exists():
                    route_path.unlink()
            else:
                return
        
        commands = ["python", "sim_single.py",
                    "-d", '"'+self.folder+'"', 
                    "-b", str(start), 
                    "-e", str(end), 
                    "-l", str(step), 
                    "-log", ','.join(logs),
                    "-seed", str(seed),
                    "--load-last-state" if self.sim_load_last_state.get() else "",
                    "--save-on-abort" if self.sim_save_on_abort.get() else "",
                    "--save-on-finish" if self.sim_save_on_finish.get() else "",
                ]
        self.destroy()
        try:
            os.system(" ".join(commands))
        except KeyboardInterrupt:
            pass
        

    def savePlugins(self):
        def _save(data:list[tuple]):
            if not self.__checkFolderOpened():
                return False
            self.setStatus("Saving plugins...")
            if self.state and "plg" in self.state:
                filename = self.state["plg"]
            else:
                filename = self.folder + "/plugins.plg.xml"
            try:
                rt = ET.Element("root")
                with open(filename, "w") as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                    for d in data:
                        attr = {"interval":str(d[1]), "enabled":str(d[2])}
                        attr.update(eval(d[4]))
                        e = ET.Element(d[0], attr)
                        if d[3] != ALWAYS_ONLINE:
                            ol = ET.Element("online")
                            lst = eval(d[3])
                            for r in lst:
                                ol.append(ET.Element("item", {"btime":str(r[0]), "etime":str(r[1])}))
                            e.append(ol)
                        rt.append(e)
                    f.write(ET.tostring(rt, "unicode", ).replace("><", ">\n<"))
                pass
            except Exception as e:
                self.setStatus(f"Error: {e}")
                showerr(f"Error saving plugins: {e}")
                return False
            self.setStatus("Plugins saved")
            return True
        return _save
    
    def __checkFolderOpened(self):
        if not self.folder:
            showerr("No project folder selected")
            return False
        return True
    
    def _loop(self):
        neww = -1
        newh = -1
        while not self._Q.empty():
            try:
                t, d = self._Q.get_nowait()
            except Empty:
                self.after(100, self._loop)
                return
            if t == "DoneOK":
                self.setStatus(_loc["STA_READY"])
            elif t == "DoneErr":
                self.setStatus(f"Error: {d}")
                showerr(f"Error: {d}")
            elif t == "Resized":
                neww, newh = d
                neww = neww - 10
                newh = newh - 80
        self.after(100, self._loop)
    
    def _load_tg(self, after:OAfter=None):
        try:
            self.tg = TrafficGenerator(self.folder)
        except Exception as e:
            showerr(f"Error loading traffic generator: {e}")
            self.tg = None
        else:
            after and after()
    
    def _load(self,loads:Optional[list[str]]=None, async_:bool = True):
        if not self.folder:
            showerr("No project folder selected")
            return
        frm = LoadingBox([
            'INST','SCS','FCS','CSCSV','ROADNET','GRID'
        ])
        if loads is None: loads = []
        self.after(100, self.__load_part2, loads, async_, frm)
    
    def __load_part2(self, loads:list[str], async_:bool, frm:LoadingBox):
        self.state = res = DetectFiles(self.folder)
        self.title(f"{_loc['TITLE']} - {self.folder}")
        
        threading.Thread(target = self._load_tg, args=(lambda:frm.setText('INST',_loc['DONE']),), daemon = True).start()
        if len(loads) == 0 or "cfg" in loads:
            if res.cfg:
                st,et,_ = get_sim_config(res.cfg)
                if st == -1: st = 0
                if et == -1: et = 172800
                self.entry_start.delete(0, END)
                self.entry_start.insert(0, str(st))
                self.entry_end.delete(0, END)
                self.entry_end.insert(0, str(et))
        if len(loads) == 0 or "fcs" in loads:
            self._load_fcs(async_, lambda: frm.setText('FCS',_loc['DONE']))
        if len(loads) == 0 or "scs" in loads:
            self._load_scs(async_, lambda: frm.setText('SCS',_loc['DONE']))
        if len(loads) == 0 or "cscsv" in loads:
            self._load_cscsv(async_, lambda: frm.setText('CSCSV',_loc['DONE']))
        if len(loads) == 0 or "grid" in loads:
            if not res.grid: 
                with open(self.folder+"/"+DEFAULT_GRID_NAME,"w") as f:
                    f.write(DEFAULT_GRID)
                self.state = res = DetectFiles(self.folder)
        if len(loads) == 0 or "plg" in loads:
            has_pdn = False
            pdn_enabled = False
            has_v2g = False
            self.sim_plglist.clear()
            if res.plg:
                for p in readXML(res.plg).getroot():
                    if p.tag.lower() == "pdn": 
                        has_pdn = True
                        attr = DEFAULT_PDN_ATTR.copy()
                    else:
                        attr = {}
                    if p.tag.lower() == "v2g": has_v2g = True
                    olelem = p.find("online")
                    if olelem is not None: ol_str = RangeList(olelem)
                    else: ol_str = ALWAYS_ONLINE
                    enabled = p.attrib.pop("enabled", SIM_YES)
                    if enabled.upper() != SIM_NO:
                        enabled = SIM_YES
                        if p.tag.lower() == "pdn": 
                            pdn_enabled = True
                    intv = p.attrib.pop("interval")
                    attr.update(p.attrib)
                    self.sim_plglist.insert("", "end", values=(
                        p.tag, intv, enabled, ol_str, repr(attr)
                    ))
            if not has_pdn:
                self.sim_plglist.insert("", "end", values=("pdn", "300", SIM_YES, ALWAYS_ONLINE, repr(DEFAULT_PDN_ATTR)))
                has_pdn = True
                pdn_enabled = True
            t = has_pdn and pdn_enabled
            tv = "enabled" if t else "disabled"
            self.sim_sta_gen.set(t)
            self.sim_cb_gen.configure(state=tv)
            self.sim_sta_bus.set(t)
            self.sim_cb_bus.configure(state=tv)
            self.sim_sta_line.set(t)
            self.sim_cb_line.configure(state=tv)
            if not has_v2g:
                self.sim_plglist.insert("", "end", values=("v2g", "300", SIM_YES, ALWAYS_ONLINE, "{}"))
                has_v2g = True
            if not res.plg:
                self.sim_plglist.save()
        self.rb_veh_src2.configure(state="normal" if "poly" in res else "disabled")
        self.rb_veh_src1.configure(state="normal" if "taz" in res else "disabled")
        self.cv_net.clear()
        self.state = res = DetectFiles(self.folder)
        if len(loads) == 0 or "net" in loads:
            self._load_network(self.tabs.select(), async_, lambda: (frm.setText('ROADNET',_loc['DONE']), frm.setText('GRID',_loc['DONE'])))
        def setText(lb:Label, itm:str, must:bool = False):
            if itm in res:
                lb.config(text=res[itm].removeprefix(self.folder), foreground="black")
            else:
                lb.config(text="None", foreground="red" if must else "black")
        
        setText(self.lb_fcs, "fcs", True)
        setText(self.lb_scs, "scs", True)
        setText(self.lb_grid, "grid")
        setText(self.lb_net, "net", True)
        setText(self.lb_veh, "veh", True)
        setText(self.lb_plg, "plg")
        setText(self.lb_cfg, "cfg")
        setText(self.lb_taz, "taz")
        setText(self.lb_py, "py")
        setText(self.lb_taz_type, "taz_type")
        setText(self.lb_osm, "osm")
        setText(self.lb_poly, "poly")
        setText(self.lb_cscsv, "cscsv")

        self.setStatus(_loc["STA_READY"])
    
    def _load_fcs(self, async_:bool = False, afterx:OAfter=None):
        def after():
            self.sim_sta_fcs.set("fcs" in self.state)
            self.sim_cb_fcs.configure(state="enabled" if "fcs" in self.state else "disabled")
            self.FCS_editor.setPoly("poly" in self.state)
            self.FCS_editor.setCSCSV("cscsv" in self.state)
            afterx and afterx()
        if self.state.fcs:
            self.FCS_editor.load(self.state.fcs, async_, after)
        else:
            self.FCS_editor.clear()
            after()
        
    def _load_scs(self, async_:bool = False, afterx:OAfter=None):
        def after():
            self.sim_sta_scs.set("scs" in self.state)
            self.sim_cb_scs.configure(state="enabled" if "scs" in self.state else "disabled")
            self.SCS_editor.setPoly("poly" in self.state)
            self.SCS_editor.setCSCSV("cscsv" in self.state)
            afterx and afterx()
        if self.state.scs:
            self.SCS_editor.load(self.state.scs, async_, after)
        else:
            self.SCS_editor.clear()
            after()

    def _load_cscsv(self, async_:bool = False, after:OAfter=None):
        if self.state.cscsv:
            self.CsCsv_editor.load(self.state.cscsv, async_, after)
        else:
            self.CsCsv_editor.clear()
            after()
    
    def _load_network(self, tab_ret, async_:bool = False, after:OAfter=None):
        if self.state and self.state.net:
            self.tabs.select(self.tab_Net)
            time.sleep(0.01)
            self.tabs.select(tab_ret)
            self.lb_gridsave.config(text=_loc["SAVED"],foreground="green")
            def work():
                if self.state.grid:
                    self.cv_net.setGrid(PowerGrid.fromFile(self.state.grid))
                self.lb_puvalues.configure(text=_loc["PU_VALS"].format(self.cv_net.Grid.Ub,self.cv_net.Grid.Sb_MVA))
                self.cv_net.setRoadNet(ELGraph(self.state.net,
                    self.state.fcs if self.state.fcs else "",
                    self.state.scs if self.state.scs else "",
                ), async_ = async_, after=after)
            if async_:
                threading.Thread(target=work,daemon=True).start()
            else:
                work()

    def openFolder(self):
        init_dir = Path("./cases")
        if not init_dir.exists(): init_dir.mkdir(parents=True, exist_ok=True)
        folder = filedialog.askdirectory(initialdir=str(init_dir),mustexist=True,title="Select project folder")
        if folder:
            self.folder = str(Path(folder))
            self._load()
    
    def generateCS(self, cscsv_mode:int, **kwargs):
        if not self.tg:
            showerr("No traffic generator loaded")
            return
        self.setStatus("Generating CS...")
        if cscsv_mode == 0:
            cs_file = ""
            poly_file = ""
        elif cscsv_mode == 1:
            cs_file = self.state.cscsv if self.state else ""
            poly_file = ""
        else:
            cs_file = ""
            poly_file = self.state.poly if self.state else ""
        kwargs["cs_file"] = cs_file
        kwargs["poly_file"] = poly_file

        def work():
            try:
                if not self.tg: return
                self.tg._CS(**kwargs)
                if kwargs["mode"] == "fcs":
                    self._load(["fcs"])
                else:
                    self._load(["scs"])
                self._Q.put(("DoneOK", None))
            except Exception as e:
                self._Q.put(("DoneErr", e))
        threading.Thread(target=work,daemon=True).start()    
    
    def generateVeh(self):
        if not self.tg:
            showerr("No traffic generator loaded")
            return
        if not self.__checkFolderOpened(): return
        self.setStatus("Generating vehicles...")
        try:
            carcnt = int(self.entry_carcnt.get())
            carseed = int(self.entry_carseed.get())
        except:
            showerr("Invalid input")
            return
        try:
            pars = self.veh_pars.getAllData()
            new_pars = {
                "v2g_prop":float(self.entry_v2gprop.get()),
                "omega":eval(pars["Omega"]),
                "krel":eval(pars["KRel"]),
                "ksc":eval(pars["KSC"]),
                "kfc":eval(pars["KFC"]),
                "kv2g":eval(pars["KV2G"]),
            }
        except:
            showerr("Invalid Vehicle parameters")
            return
        if self.veh_gen_src.get() == 0:
            mode = "Auto"
        elif self.veh_gen_src.get() == 1:
            mode = "TAZ"
        else:
            mode = "Poly"
        def work():
            try:
                assert self.tg
                self.tg.EVTrips(carcnt, carseed, mode = mode, **new_pars)
                self._load(["veh"])
                self._Q.put(("DoneOK", None))
            except Exception as e:
                self._Q.put(("DoneErr", e))
        threading.Thread(target=work,daemon=True).start()

    def draw(self):
        if not self.__checkFolderOpened(): return
        self.cv_net.UnlocateAllEdges()
        s = set(x.strip() for x in self.entry_locedges.get().split(','))
        self.cv_net.LocateEdges(s)

    def CSCSVDownloadWorker(self):
        if not self.__checkFolderOpened(): return
        self.setStatus("Downloading CS CSV...")
        key = self.CsCsv_editor.entry_amapkey.get()
        def work():
            try:
                csQuery(self.folder,"",key,True)
                self._load(["cscsv"])
            except Exception as e:
                self._Q.put(('DoneErr', f"Error downloading CS CSV: {e}"))
                return
            self._Q.put(('DoneOK',None))
        threading.Thread(target=work,daemon=True).start()
        
    def setStatus(self, text:str):
        self.sbar.config(text=text)

    def _win(self):
        self.title(_loc["TITLE"])

if __name__ == "__main__":
    _loc.DefaultLanguage = Lang.get_lang_code()
    win = MainBox()
    win.mainloop()