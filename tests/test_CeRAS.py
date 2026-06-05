# tests/test_CeRAS.py

"""Run the CeRAS fixture through Python dictionaries and compare FAST output."""

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
            'EIS': 2005,
            'Class': 'Turbofan',
            'MaxPax': 218.88276438829473
        },
        'Aero': {
            'L_D': {
                'ClbCF': 1,
                'CrsCF': 1,
                'Clb': 13,
                'Crs': 17,
                'Des': 13
            },
            'W_S': {
                'SLS': 739.84991686200692
            }
        },
        'Propulsion': {
            'MDotCF': 1.2,
            'PropArch': {
                'Type': 'C'
            },
            'Engine': {
                'Mach': 0.050000000000000003,
                'Alt': 0,
                'OPR': 24.5,
                'FPR': 1.6000000000000001,
                'BPR': 4,
                'Tt4Max': 1711,
                'TempLimit': {
                    'Val': nan,
                    'Type': nan
                },
                'DesignThrust': 64543.695637429853,
                'NoSpools': 2,
                'RPMs': row([7400, 17820]),
                'FanGearRatio': nan,
                'FanBoosters': False,
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
                    'Compressors': 0.93999999999999995,
                    'BypassNozzle': 0.98999999999999999,
                    'Combustor': 0.995,
                    'Turbines': 0.93999999999999995,
                    'CoreNozzle': 0.98999999999999999,
                    'Nozzles': 0.98999999999999999,
                    'Mixing': 0
                },
                'PerElec': 0,
                'Cff3': 0.29899999999999999,
                'Cff2': -0.34599999999999997,
                'Cff1': 0.70099999999999996,
                'Cffch': 7.9999999999999996e-07,
                'HEcoeff': 1
            },
            'NumEngines': 2,
            'T_W': {
                'SLS': 0.29999999999999999
            },
            'Eta': {
                'Prop': 0.80000000000000004
            }
        },
        'Weight': {
            'WairfCF': 1,
            'MTOW': 86182.550300000003,
            'EG': nan,
            'EM': 0,
            'Fuel': 9427.9174104499998,
            'Batt': 0
        },
        'Performance': {
            'Vels': {
                'Tko': 69.450000000000074,
                'Crs': 0.78000000000000003
            },
            'Alts': {
                'Tko': 0,
                'Crs': 10668
            },
            'Range': 4630000,
            'RCMax': 11.430000000000001
        },
        'Power': {
            'SpecEnergy': {
                'Fuel': 12,
                'Batt': 0.25
            },
            'LamDwn': {
                'SLS': 0,
                'Tko': 0,
                'Clb': 0,
                'Crs': 0,
                'Des': 0,
                'Lnd': 0
            },
            'LamUps': {
                'SLS': 0,
                'Tko': 0,
                'Clb': 0,
                'Crs': 0,
                'Des': 0,
                'Lnd': 0
            },
            'Eta': {
                'EM': 0.95999999999999996,
                'EG': 0.95999999999999996
            },
            'P_W': {
                'SLS': nan,
                'EM': 10,
                'EG': nan
            },
            'Battery': {
                'ParCells': nan,
                'SerCells': nan,
                'BegSOC': nan
            }
        }
    },
    'Settings': {
        'TkoPoints': nan,
        'ClbPoints': nan,
        'CrsPoints': nan,
        'DesPoints': nan,
        'OEW': {
            'MaxIter': 50,
            'Tol': 0.001
        },
        'Analysis': {
            'MaxIter': 50,
            'Type': 1
        },
        'Plotting': 0,
        'Table': 0
    }
}

MISSION = {
    'Target': {
        'Valu': [1620500, 3009500],
        'Type': ['Dist', 'Dist']
    },
    'Segs': ['Climb', 'Cruise', 'Climb', 'Cruise', 'Descent'],
    'ID': [1, 1, 2, 2, 2],
    'AltBeg': [0, 10058.4, 10058.4, 10668, 10668],
    'AltEnd': [10058.4, 10058.4, 10668, 10668, 0],
    'VelBeg': [0.20000000000000001, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003],
    'VelEnd': [0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.78000000000000003, 0.20000000000000001],
    'TypeBeg': ['Mach', 'Mach', 'Mach', 'Mach', 'Mach'],
    'TypeEnd': ['Mach', 'Mach', 'Mach', 'Mach', 'Mach'],
    'ClbRate': [nan, nan, nan, nan, nan]
}



def test_CeRAS_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full CeRAS aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name='CeRAS',
        aircraft=AIRCRAFT,
        mission=MISSION,
        saved='CeRAS/outputs/OutputAircraft.mat',
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
