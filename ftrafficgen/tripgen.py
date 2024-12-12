from ftrafficgen.poly import PolygonMan
import random, time, sumolib
from typing import Literal, Optional
from feasytools import ReadOnlyTable
import numpy as np
from flocale import Lang
from .misc import random_diff, TripInner, _EV, _xmlSaver
from ftraffic import EV, EVDict, readXML, DetectFiles


TAZ_TYPE_LIST = ["Home", "Work", "Relax", "Other"]
def _type2strplace(type: int) -> str:
    """
    Convert 0, 1, 2, 3 to "Home", "Work", "Relax", "Other"
    """
    return TAZ_TYPE_LIST[type]


class EVsGenerator:    
    """Class to generate trips"""
    def __init__(self, CROOT: str, PNAME: str, seed, mode: Literal["Auto", "Poly", "TAZ"] = "Auto"):
        """
        Initialization
            CROOT: Trip parameter folder
            PNAME: SUMO configuration folder
            seed: Random seed
        """
        _fn = DetectFiles(PNAME)
        random.seed(seed)
        self.vTypes = ReadOnlyTable(CROOT + "/ev_types.csv",dtype=np.float32).to_list_of_dict()
        # Define various functional area types
        self.dic_taz = {}
        self.net:sumolib.net.Net = sumolib.net.readNet(_fn["net"])
        if mode == "Auto":
            if _fn.taz and _fn.taz_type: mode = "TAZ"
            elif _fn.poly and _fn.net and _fn.fcs: mode = "Poly"
            else: raise RuntimeError(Lang.ERROR_NO_TAZ_OR_POLY)
        if mode == "TAZ":
            assert _fn.taz and _fn.taz_type, Lang.ERROR_NO_TAZ_OR_POLY
            self._mode = "taz"
            self.dic_taztype = {}
            with open(_fn.taz_type, "r") as fp:
                for ln in fp.readlines():
                    name, lst = ln.split(":")
                    self.dic_taztype[name.strip()] = [x.strip() for x in lst.split(",")]
            root = readXML(_fn.taz).getroot()
            for taz in root.findall("taz"):
                taz_id = taz.attrib["id"]
                if "edges" in taz.attrib:
                    self.dic_taz[taz_id] = taz.attrib["edges"].split(" ")
                else:
                    self.dic_taz[taz_id] = [edge.attrib["id"] for edge in taz.findall("tazSource")]
        elif mode == "Poly":
            assert _fn.poly and _fn.net and _fn.fcs, Lang.ERROR_NO_TAZ_OR_POLY
            self._mode = "poly"
            from .graph import ELGraph
            net = ELGraph(_fn.net, _fn.fcs)
            polys = PolygonMan(_fn.poly)
            self.dic_taztype = {k:[] for k in TAZ_TYPE_LIST}
            for poly in polys:
                taz_id = poly.ID
                taz_type = poly.getConvertedType()
                poi_pos = poly.center()
                if taz_type:
                    try:
                        eid = net.find_nearest_edge_id(poi_pos)
                    except RuntimeError:
                        continue
                    self.dic_taztype[taz_type].append(taz_id)
                    self.dic_taz[taz_id] = [eid]
        else:
            raise RuntimeError(Lang.ERROR_NO_TAZ_OR_POLY)

        # Read spatial transfer probability
        self.PSweekday:dict[str,ReadOnlyTable] = {}
        self.PSweekend:dict[str,ReadOnlyTable] = {}
        self.cdfweekday:dict[str,ReadOnlyTable] = {}
        self.cdfweekend:dict[str,ReadOnlyTable] = {}
        for dtype in TAZ_TYPE_LIST:
            self.PSweekday[dtype] = ReadOnlyTable(
                f"{CROOT}/space_transfer_probability/{dtype[0]}_spr_weekday.csv",
                dtype=np.float32
            )
            self.PSweekend[dtype] = ReadOnlyTable(
                f"{CROOT}/space_transfer_probability/{dtype[0]}_spr_weekend.csv",
                dtype=np.float32
            )
            self.cdfweekday[dtype] = ReadOnlyTable(
                f"{CROOT}/duration_of_parking/{dtype[0]}_spr_weekday.csv",
                dtype=np.float32
            )
            self.cdfweekend[dtype] = ReadOnlyTable(
                f"{CROOT}/duration_of_parking/{dtype[0]}_spr_weekend.csv",
                dtype=np.float32
            )

        soc_pdf = ReadOnlyTable(f"{CROOT}/soc_dist.csv",dtype=np.int32)
        self.soc_vals:list[int] = soc_pdf.col("range").tolist()
        self.soc_freq:list[int] = soc_pdf.col("freq").tolist()
    
    def __getPs(self, is_weekday: bool, dtype: str) -> ReadOnlyTable:
        return self.PSweekday[dtype] if is_weekday else self.PSweekend[dtype]

    def __getcdf(self, is_weekday: bool, dtype: str) -> ReadOnlyTable:
        return self.cdfweekday[dtype] if is_weekday else self.cdfweekend[dtype]

    def __genSoC(self):
        return random.choices(self.soc_vals, self.soc_freq)[0] / 100.0

    @staticmethod
    def __find_first_greater_than(lst:np.ndarray, val:float):
        for i, v in enumerate(lst):
            if v > val:
                return i
        return len(lst)
    
    def __getDest1(self, pfr: str, weekday: bool = True):
        """
        获取第一次行程的下一次行程目的地
            pfr: Departure functional area type, such as "Home"
            weekday: Whether it is weekday or weekend
        Returns: 
            First trip: First departure time, arrival destination functional area type, such as "Work"
        """
        while True:
            while True:
                if weekday:
                    init_time = random.gammavariate(6.63, 65.76) + 114.54
                else:
                    init_time = random.gammavariate(3.45, 84.37) + 197.53
                place = pfr
                init_time_i = int(init_time / 15)
                ps = self.__getPs(weekday, place)
                if init_time_i < len(ps.head):
                    break
            data = ps.col(init_time_i)
            cdf = np.cumsum(data)
            if not cdf[3] == 0:
                break
        x = random.random()
        next_place = _type2strplace(EVsGenerator.__find_first_greater_than(cdf, x))
        return int(init_time), next_place

    def __getDestA(self, from_type:str, init_time_i:int, weekday: bool):
        """
        获取非第一次行程的下一次行程目的地 | Get the destination of the next trip for non-first trips
            from_type:出发地类型, 例如“Home” | Departure type, such as "Home"
            depart_time:出发时间 | Departure time
        返回 | Returns:
            目的地类型 | Destination type
        """
        data = self.__getPs(weekday, from_type).col(init_time_i)
        cdf = np.cumsum(data) * 15
        return ("Home" if cdf[3] == 0 else _type2strplace(
            EVsGenerator.__find_first_greater_than(cdf, random.random())
        ))

    def __getNextTAZandPlace(self, from_TAZ:str, from_EDGE:str, next_place_type:str) -> tuple[str,str,list[str]]:
        trial = 0
        while True:
            if self._mode == "taz":
                to_TAZ = random.choice(self.dic_taztype[next_place_type])
                to_EDGE = random_diff(self.dic_taz[to_TAZ], from_EDGE)
            else: # self._mode == "diff"
                to_TAZ = random_diff(self.dic_taztype[next_place_type], from_TAZ)
                to_EDGE = random.choice(self.dic_taz[to_TAZ])
            if from_EDGE != to_EDGE:
                return to_TAZ, to_EDGE, [from_EDGE, to_EDGE]
            trial += 1
            if trial >= 5:
                raise RuntimeError("from_EDGE == to_EDGE")
        
    
    def __genFirstTrip1(self, trip_id, weekday: bool = True):
        """
        生成首日的第1个行程 | Generate the first trip of the first day
            trip_id: 行程id | Trip ID
            weekday: 是否是工作日 | Whether it is weekday or weekend
        返回trip的xml文件行、字典形式保存的相关信息 | Return the trip's XML file line and the relevant information saved in dictionary form
            dic_save = {
                "trip_id":...,          #行程id | Trip ID
                "depart_time":...,      #第一次行程出发时间/min | Departure time of the first trip
                "from_TAZ":...,         #第一次行程出发区域TAZ类型“TAZ1” | Departure area TAZ type "TAZ1"
                "from_EDGE":...,        #出发道路边, 例如“gnE29” | Departure roadside, such as "gnE29"
                "to_TAZ":...,           #第一次行程到达区域TAZ类型“TAZ2” | Arrival area TAZ type "TAZ2"
                "to_EDGE":...,          #到达道路边, 例如“gnE2” | Arrival roadside, such as "gnE2"
                "routes":...,           #SUMO xml文件读取的routes类型'gneE22 gneE0 gneE16' | Routes type read from SUMO xml file 'gneE22 gneE0 gneE16'
                "next_place_type":...   #到达区域属性“Work” | Arrival area attribute "Work"
            }
        """
        # 出发TAZ区域编号,例如“TAZ1”
        from_TAZ = random.choice(self.dic_taztype["Home"])
        # 出发道路边,例如“gnE29”
        from_EDGE = random.choice(self.dic_taz[from_TAZ])
        # 得到出发时间和目的地区域类型 | Get departure time and destination area type
        depart_time, next_place_type = self.__getDest1("Home", weekday)  
        to_TAZ, to_EDGE, route = self.__getNextTAZandPlace(from_TAZ, from_EDGE, next_place_type)
        return TripInner(trip_id, depart_time, from_TAZ, from_EDGE,
            to_TAZ, to_EDGE, route, next_place_type)

    cdf_dict = {}

    def __genStopTime(self, from_type, weekday: bool):
        cdf = np.cumsum(self.__getcdf(weekday, from_type).col("0")) * 15
        # 停留时长单位为15min, 抽取停留时间 | The unit of stay time is 15min, extract the stay time
        return EVsGenerator.__find_first_greater_than(cdf, random.random()) + 1

    def __genTripA(
        self, trip_id, from_TAZ, from_type, from_EDGE, start_time, weekday: bool = True
    )->TripInner:
        """生成第2个行程 | Generate the second trip"""
        stop_duration = self.__genStopTime(from_type, weekday)
        depart_time = start_time + stop_duration * 15 + 20
        next_place2 = self.__getDestA(from_type, stop_duration, weekday)
        taz_choose2, edge_choose2, route = self.__getNextTAZandPlace(from_TAZ, from_EDGE, next_place2)
        return TripInner(trip_id, depart_time, from_TAZ, from_EDGE,
            taz_choose2, edge_choose2, route, next_place2)

    def __genTripF(
        self, trip_id:str, from_TAZ:str, from_type, from_EDGE:str,
        start_time:int, first_TAZ:str, first_EDGE:str, weekday: bool = True,
    ):
        """生成第3个行程 | Generate the third trip"""
        if first_EDGE == from_EDGE:
            return None
        stop_time = self.__genStopTime(from_type, weekday)
        depart_time = start_time + stop_time + 20
        return TripInner(
            trip_id, depart_time, from_TAZ, from_EDGE, first_TAZ, first_EDGE,
            [from_EDGE, first_EDGE], "Home"
        )

    def __genTripsChain1(self, vehicle_id: str, v2g_prop: float):  # vehicle_trip
        """
        生成首日一整天的出行链 | Generate a full day of trips on the first day
            vehicle_id: 车辆ID | Vehicle ID
            v2g_prop: 愿意V2G的概率 | Probability of willing to V2G
        """
        daynum = 0
        weekday = True
        ev = _EV(vehicle_id, random.choice(self.vTypes), self.__genSoC(), v2g_prop)
        trip_1 = self.__genFirstTrip1("trip0_1", weekday)
        trip_2 = self.__genTripA("trip0_2",trip_1.toTAZ,
            trip_1.NTP,trip_1.toE,trip_1.DPTT,weekday)
        trip_3 = self.__genTripF("trip0_3",trip_2.toTAZ,
            trip_2.NTP,trip_2.toE,trip_2.DPTT,
            trip_1.frTAZ,trip_1.route[0],weekday)
        
        ev.add_trip(daynum, trip_1)
        ev.add_trip(daynum, trip_2)
        if trip_3: # Trip3如果起点等于终点则不生成
            ev.add_trip(daynum, trip_3)
        return ev

    def __genFirstTripA(self, trip_id, ev: _EV, weekday: bool = True):
        """
        生成非首日的第1段行程 | Generate the first trip of a non-first day
            trip_id: 行程id | Trip ID
            vehicle_node: 车辆节点, 如rootNode.getElementsByTagName("vehicle")[0] | Vehicle node, such as rootNode.getElementsByTagName("vehicle")[0]
            weekday: 是否是工作日 | Whether it is weekday or weekend
        """
        trip_last = ev.trips[-1]
        from_EDGE = trip_last.route[-1]
        from_TAZ = trip_last.toTAZ
        # 得到出发时间和目的地区域类型 | Get departure time and destination area type
        depart_time, next_place_type = self.__getDest1("Home", weekday)
        to_TAZ, to_EDGE, route = self.__getNextTAZandPlace(from_TAZ, from_EDGE, next_place_type)
        return TripInner(trip_id, depart_time, from_TAZ, from_EDGE,
            to_TAZ, to_EDGE, route, next_place_type)

    def __genTripsChainA(self, ev: _EV, daynum: int = 1):  # vehicle_trip
        """
        生成非首日一整天的出行链 | Generate a full day of trips on a non-first day
        """
        weekday = (daynum - 1) % 7 + 1 in [1, 2, 3, 4, 5]
        trip2_1 = self.__genFirstTripA(f"trip{daynum}_1", ev, weekday)
        trip2_2 = self.__genTripA(f"trip{daynum}_2",trip2_1.toTAZ,
            trip2_1.NTP,trip2_1.toE,trip2_1.DPTT,weekday)
        trip2_3 = self.__genTripF(f"trip{daynum}_3",
            trip2_2.toTAZ,trip2_2.NTP,trip2_2.toE,
            trip2_2.DPTT,trip2_1.frTAZ,trip2_1.route[0],weekday)
                    
        ev.add_trip(daynum, trip2_1)
        ev.add_trip(daynum, trip2_2)
        if trip2_3:
            ev.add_trip(daynum, trip2_3)

    def __genEV(self, veh_id: str, v2g_prop: float) -> _EV:
        ev = self.__genTripsChain1(veh_id, v2g_prop)
        for j in range(1, 8):
            self.__genTripsChainA(ev, j)
        return ev

    def genEV(self, veh_id: str, v2g_prop: float) -> EV:
        """
        生成一辆车一整周的出行链 | Generate a full week of trips for a vehicle
        """
        return self.__genEV(veh_id, v2g_prop).to_EV()

    def genEVs(
        self, N: int, v2g_prop: float, fname: Optional[str] = None, silent: bool = False
    ) -> EVDict:
        """
        生成EV和行程 | Generate EV and trips
            N: 车辆数 | Number of vehicles
            v2g_prop: 愿意参加V2G的用户比例 | Proportion of users willing to participate in V2G
            fname: 保存的文件名(为None则不保存) | Saved file name (if None, not saved)
            silent: 是否静默模式 | Whether silent mode
        """
        st_time = time.time()
        last_print_time = 0
        saver = _xmlSaver(fname) if fname else None
        ret = EVDict()
        for i in range(0, N):
            ev = self.__genEV("v" + str(i), v2g_prop)
            ret.add(ev.to_EV())
            if saver:
                saver.write(ev)
            if not silent and time.time()-last_print_time>1:
                print(f"\r{i+1}/{N}, {(i+1)/N*100:.2f}%", end="")
                last_print_time=time.time()
        if not silent:
            print(f"\r{N}/{N}, 100.00%")
            print(Lang.INFO_DONE_WITH_SECOND.format(round(time.time() - st_time, 1)))
        if saver:
            saver.close()
        return ret