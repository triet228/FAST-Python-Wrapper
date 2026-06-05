# tests/test_A320.py

"""Run the A320 fixture through Python dictionaries and compare FAST output."""

from wrapper import MatlabRow as row, matlab_expr as m

nan = float("nan")

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


AIRCRAFT = {
    'Specs': {
        'TLAR': {
            'EIS': 2016,
            'Class': 'Turbofan',
            'MaxPax': 161.14736842105262
        },
        'Aero': {
            'L_D': {
                'ClbCF': 1,
                'CrsCF': 1,
                'Clb': 16,
                'Crs': 18.23,
                'Des': 16
            },
            'W_S': {
                'SLS': 624.50592885375499
            }
        },
        'Propulsion': {
            'MDotCF': 1,
            'PropArch': {
                'Type': 'C'
            },
            'Engine': {
                'Mach': 0.050000000000000003,
                'Alt': 0,
                'OPR': 50,
                'FPR': 1.3999999999999999,
                'BPR': 11,
                'Tt4Max': 1593,
                'TempLimit': {
                    'Val': nan,
                    'Type': nan
                },
                'DesignThrust': 120640,
                'NoSpools': 2,
                'RPMs': row([3894, 19391]),
                'FanGearRatio': nan,
                'FanBoosters': True,
                'CoreFlow': {
                    'PaxBleed': 0.029999999999999999,
                    'Leakage': 0.01,
                    'Cooling': 0
                },
                'MaxIter': 300,
                'EtaPoly': {
                    'Inlet': 0.98999999999999999,
                    'Diffusers': 0.98999999999999999,
                    'Fan': 0.98999999999999999,
                    'Compressors': 0.95999999999999996,
                    'BypassNozzle': 0.98999999999999999,
                    'Combustor': 0.995,
                    'Turbines': 0.95999999999999996,
                    'CoreNozzle': 0.98999999999999999,
                    'Nozzles': 0.98999999999999999,
                    'Mixing': 0
                },
                'Cff3': 0.40060000000000001,
                'Cff2': -0.43230000000000002,
                'Cff1': 0.99460000000000004,
                'Cffch': 6.0999999999999998e-07,
                'HEcoeff': 1
            },
            'NumEngines': 2,
            'T_W': {
                'SLS': 0.32869416879901808
            },
            'Thrust': {
                'SLS': 237000
            },
            'Eta': {
                'Prop': 0.80000000000000004
            }
        },
        'Weight': {
            'WairfCF': 1,
            'MTOW': 79000,
            'EG': nan,
            'EM': nan,
            'Fuel': 19000,
            'Batt': nan
        },
        'Performance': {
            'Vels': {
                'Tko': 69.450000000000074,
                'Crs': 0.81999999999999995
            },
            'Alts': {
                'Tko': 0,
                'Crs': 10668
            },
            'Range': 4815000,
            'RCMax': 11.43
        },
        'Power': {
            'SpecEnergy': {
                'Fuel': 12,
                'Batt': nan
            },
            'Eta': {
                'EM': nan,
                'EG': nan
            },
            'P_W': {
                'SLS': nan,
                'EM': nan,
                'EG': nan
            },
            'LamUps': {
                'SLS': 0,
                'Tko': 0,
                'Clb': 0,
                'Crs': 0,
                'Des': 0,
                'Lnd': 0
            },
            'LamDwn': {
                'SLS': 0,
                'Tko': 0,
                'Clb': 0,
                'Crs': 0,
                'Des': 0,
                'Lnd': 0
            },
            'Battery': {
                'ParCells': nan,
                'SerCells': nan,
                'BegSOC': nan
            }
        }
    },
    'Settings': {
        'TkoPoints': 4,
        'ClbPoints': 5,
        'CrsPoints': 5,
        'DesPoints': 5,
        'OEW': {
            'MaxIter': 50,
            'Tol': 0.001
        },
        'Analysis': {
            'MaxIter': 50,
            'Type': 1
        },
        'Plotting': 1,
        'Table': 0,
        'VisualizeAircraft': 0
    }
}

MISSION = {
    'Target': {
        'Valu': [2098933.333333333, 2098933.333333333, 2098933.333333333, 370400, 30],
        'Type': ['Dist', 'Dist', 'Dist', 'Dist', 'Time']
    },
    'Segs': ['Takeoff', 'Climb', 'Climb', 'Cruise', 'Climb', 'Cruise', 'Climb', 'Cruise', 'Descent', 'Climb', 'Cruise', 'Descent', 'Cruise', 'Descent', 'Landing'],
    'ID': [1, 1, 1, 1, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5],
    'AltBeg': [0, 0, 3048, 10668, 10668, 11277.6, 11277.6, 11887.200000000001, 11887.200000000001, 457.20000000000005, 4572, 4572, 457.20000000000005, 457.20000000000005, 0],
    'AltEnd': [0, 3048, 10668, 10668, 11277.6, 11277.6, 11887.200000000001, 11887.200000000001, 457.20000000000005, 4572, 4572, 457.20000000000005, 457.20000000000005, 0, 0],
    'ClbRate': [nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan],
    'VelBeg': [0, 0.29999999999999999, 128.61111111111126, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999],
    'VelEnd': [0.29999999999999999, 128.61111111111126, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0.29999999999999999, 0],
    'TypeBeg': ['Mach', 'Mach', 'TAS', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach'],
    'TypeEnd': ['Mach', 'TAS', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach', 'Mach']
}



def test_A320_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full A320 aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name='A320',
        aircraft=AIRCRAFT,
        mission=MISSION,
        saved='A320/outputs/OutputAircraft.mat',
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
