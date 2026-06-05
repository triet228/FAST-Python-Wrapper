# main.py
from wrapper import FastWrapper, matlab_expr


nan = float("nan")
m = matlab_expr

AIRCRAFT = {
    "Specs": {
        "TLAR": {
            "EIS": 2005,
            "Class": "Turbofan",
            "MaxPax": 78,
        },
        "Aero": {
            "L_D": {
                "ClbCF": 1.002,
                "CrsCF": 1.000,
                "Clb": 10.9773 * 1.002,
                "Crs": 15.2000 * 1.000,
                "Des": 10.9773 * 1.002,
            },
            "W_S": {
                "SLS": m(
                    'UnitConversionPkg.ConvMass(109.25, "lbm", "kg") / '
                    '(UnitConversionPkg.ConvLength(1, "ft", "m")) ^ 2'
                ),
            },
        },
        "Battery": {
            "NomVolCell": 3.6,
            "MaxExtVolCell": 4.0880,
            "CapCell": 3,
            "IntResist": 0.0199,
            "expVol": 0.0986,
            "expCap": 30,
            "MinSOC": 20,
            "BegSOC": 100,
            "MaxAllowCRate": 5,
            "Charging": 500 * 1000,
        },
        "Performance": {
            "Vels": {
                "Tko": m('UnitConversionPkg.ConvVel(135, "kts", "m/s")'),
                "Crs": 0.78,
            },
            "Alts": {
                "Tko": 0,
                "Crs": m('UnitConversionPkg.ConvLength(35000, "ft", "m")'),
            },
            "Range": m('UnitConversionPkg.ConvLength(2150, "naut mi", "m")'),
            "RCMax": m('UnitConversionPkg.ConvVel(2250, "ft/min", "m/s")'),
        },
        "Weight": {
            "MTOW": m('UnitConversionPkg.ConvMass(85517, "lbm", "kg")'),
            "EG": nan,
            "EM": 0,
            "Fuel": m('UnitConversionPkg.ConvMass(20785, "lbm", "kg")'),
            "Batt": 0,
            "WairfCF": 1.018,
        },
        "Propulsion": {
            "MDotCF": 1.029,
            "PropArch": "O",
            "Engine": m("EngineModelPkg.EngineSpecsPkg.CF34_8E5"),
            "NumEngines": 2,
            "T_W": {
                "SLS": 0.3393,
            },
            "Thrust": {
                "SLS": m('UnitConversionPkg.ConvForce(2 * 14510, "lbf", "N")'),
            },
            "Eta": {
                "Prop": 0.8,
            },
        },
        "Power": {
            "SpecEnergy": {
                "Fuel": 12,
                "Batt": 0.25,
            },
            "Eta": {
                "EM": 0.96,
                "EG": nan,
            },
            "P_W": {
                "SLS": nan,
                "EM": 10,
                "EG": nan,
            },
            "LamUps": {
                "SLS": 1,
                "Tko": 1,
                "Clb": 1,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "LamDwn": {
                "SLS": 0.1,
                "Tko": 0.1,
                "Clb": 0.01,
                "Crs": 0,
                "Des": 0,
                "Lnd": 0,
            },
            "Battery": {
                "ParCells": 100,
                "SerCells": 62,
                "BegSOC": 100,
            },
        },
    },
    "Settings": {
        "TkoPoints": nan,
        "ClbPoints": nan,
        "CrsPoints": nan,
        "DesPoints": nan,
        "OEW": {
            "MaxIter": 50,
            "Tol": 0.001,
        },
        "Analysis": {
            "MaxIter": 30,
            "Type": 1,
        },
        "Degradation": 0,
        "PowerOpt": 0,
        "PowerStrat": -1,
        "ConSOC": 1,
        "Plotting": 0,
        "Table": 0,
        "PrintOut": 1,
    },
}


MISSION = {
    "Target": {
        "Valu": [
            m("Aircraft.Specs.Performance.Range"),
            m('UnitConversionPkg.ConvLength(100, "naut mi", "m")'),
            45,
        ],
        "Type": ["Dist", "Dist", "Time"],
    },
    "Segs": [
        "Takeoff",
        "Climb",
        "Climb",
        "Climb",
        "Cruise",
        "Descent",
        "Descent",
        "Descent",
        "Climb",
        "Climb",
        "Climb",
        "Cruise",
        "Cruise",
        "Descent",
        "Descent",
        "Descent",
        "Landing",
    ],
    "ID": [1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3],
    "AltBeg": [
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(1500, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Tko"),
    ],
    "AltEnd": [
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m("Aircraft.Specs.Performance.Alts.Crs"),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(1500, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(10000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(9000, "ft", "m")'),
        m('UnitConversionPkg.ConvLength(3000, "ft", "m")'),
        m("Aircraft.Specs.Performance.Alts.Tko"),
        m("Aircraft.Specs.Performance.Alts.Tko"),
    ],
    "VelBeg": [
        0,
        m("Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
    ],
    "VelEnd": [
        m("Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m("Aircraft.Specs.Performance.Vels.Crs"),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(210, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(250, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m('UnitConversionPkg.ConvVel(200, "kts", "m/s")'),
        m("1.2 * Aircraft.Specs.Performance.Vels.Tko"),
        0,
    ],
    "TypeBeg": [
        "TAS",
        "TAS",
        "EAS",
        "EAS",
        "Mach",
        "Mach",
        "EAS",
        "EAS",
        "TAS",
        "EAS",
        "EAS",
        "TAS",
        "TAS",
        "TAS",
        "EAS",
        "EAS",
        "TAS",
    ],
    "TypeEnd": [
        "TAS",
        "EAS",
        "EAS",
        "Mach",
        "Mach",
        "EAS",
        "EAS",
        "TAS",
        "EAS",
        "EAS",
        "TAS",
        "TAS",
        "TAS",
        "EAS",
        "EAS",
        "TAS",
        "TAS",
    ],
    "ClbRate": [nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan],
}


FAN_EFFICIENCY = 0.99
EM_EFFICIENCY = 0.96
GRAPH_BASED_PROPULSION = {
    "Arch": [
        [0, 0, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0],
    ],
    "OperUps": m(
        "@(lam) ["
        "0, 0, 1/2, 1/2, 0, 0, 0, 0, 0; "
        "0, 0, 0, 0, 1/2, 1/2, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 1, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, 1, 0; "
        "0, 0, 0, 0, 0, 0, lam, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, lam, 0; "
        "0, 0, 0, 0, 0, 0, 0, 0, 1; "
        "0, 0, 0, 0, 0, 0, 0, 0, 1; "
        "0, 0, 0, 0, 0, 0, 0, 0, 0]"
    ),
    "OperDwn": m(
        "@(lam) ["
        "0, 0, 0, 0, 0, 0, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 0, 0, 0; "
        "1, 0, 0, 0, 0, 0, 0, 0, 0; "
        "1, 0, 0, 0, 0, 0, 0, 0, 0; "
        "0, 1, 0, 0, 0, 0, 0, 0, 0; "
        "0, 1, 0, 0, 0, 0, 0, 0, 0; "
        "0, 0, 1-lam, 0, lam, 0, 0, 0, 0; "
        "0, 0, 0, 1-lam, 0, lam, 0, 0, 0; "
        "0, 0, 0, 0, 0, 0, 1/2, 1/2, 0]"
    ),
    "EtaUps": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, EM_EFFICIENCY, EM_EFFICIENCY, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1],
        [1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, FAN_EFFICIENCY, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
    "EtaDwn": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, EM_EFFICIENCY, 1, 1, 1, 1, 1, 1, 1],
        [1, EM_EFFICIENCY, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, FAN_EFFICIENCY, 1, FAN_EFFICIENCY, 1, 1, 1, 1],
        [1, 1, 1, FAN_EFFICIENCY, 1, FAN_EFFICIENCY, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
    "SrcType": [1, 0],
    "TrnType": [1, 1, 0, 0, 2, 2],
}


if AIRCRAFT["Specs"]["Propulsion"]["PropArch"].upper() == "O":
    AIRCRAFT["Specs"]["Propulsion"]["PropArchGraph"] = GRAPH_BASED_PROPULSION


def main():
    with FastWrapper() as fast:
        result = fast.run(aircraft=AIRCRAFT, mission=MISSION)

    print(result)


if __name__ == "__main__":
    main()
