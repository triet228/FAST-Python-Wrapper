# tests/test_ATR42.py

"""Run the ATR42 fixture through Python dictionaries and compare FAST output."""

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
            'EIS': nan,
            'Class': 'Turboprop',
            'MaxPax': 48
        },
        'Performance': {
            'Vels': {
                'Tko': nan,
                'Crs': 0.40000000000000002
            },
            'Alts': {
                'Tko': nan,
                'Crs': 7620
            },
            'Range': 1326000,
            'RCMax': 7.4930000000000003
        },
        'Aero': {
            'L_D': {
                'Clb': 10,
                'Crs': 12,
                'Des': nan
            },
            'W_S': {
                'SLS': 342
            }
        },
        'Weight': {
            'MTOW': 18600,
            'Fuel': 4500,
            'MLW': nan,
            'Batt': nan,
            'EM': nan,
            'EG': nan
        },
        'Propulsion': {
            'PropArch': {
                'Type': 'C'
            },
            'T_W': {
                'SLS': nan
            },
            'Eta': {
                'Prop': 0.80000000000000004
            },
            'Engine': {
                'Mach': 0.050000000000000003,
                'Alt': 0,
                'OPR': 14.699999999999999,
                'Tt4Max': 1110,
                'ReqPower': 2051000,
                'NPR': 1.3,
                'NoSpools': 3,
                'RPMs': row([28870, 33300, 1200]),
                'EtaPoly': {
                    'Inlet': 0.98999999999999999,
                    'Diffusers': 0.98999999999999999,
                    'Compressors': 0.88,
                    'Combustor': 0.995,
                    'Turbines': 0.88,
                    'Nozzles': 0.98499999999999999
                }
            }
        },
        'Power': {
            'SLS': nan,
            'SpecEnergy': {
                'Fuel': 12,
                'Batt': 0.34999999999999998
            },
            'Eta': {
                'EM': 0.95999999999999996,
                'EG': 0.95999999999999996
            },
            'P_W': {
                'SLS': 0.1731,
                'EM': nan,
                'EG': nan
            },
            'Battery': {
                'SerCells': nan,
                'ParCells': nan,
                'BegSOC': nan
            }
        }
    },
    'Settings': {
        'Analysis': {
            'Type': 1
        },
        'Plotting': 0
    }
}

MISSION = {
    'Target': {
        'Valu': [1301956, 277800, 45],
        'Type': ['Dist', 'Dist', 'Time']
    },
    'Segs': ['Takeoff', 'Climb', 'Cruise', 'Descent', 'Descent', 'Climb', 'Cruise', 'Cruise', 'Descent', 'Descent', 'Landing'],
    'ID': [1, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3],
    'AltBeg': [0, 0, 7620, 7620, 914.40000000000009, 457.20000000000005, 4572, 4572, 4572, 914.40000000000009, 457.20000000000005],
    'AltEnd': [0, 7620, 7620, 914.40000000000009, 457.20000000000005, 4572, 4572, 4572, 914.40000000000009, 457.20000000000005, 0],
    'ClbRate': [nan, nan, nan, -6.0960000000000001, nan, nan, nan, nan, -6.0960000000000001, nan, nan],
    'VelBeg': [0, 82.311111111111202, 102.88888888888901, 102.88888888888901, 102.88888888888901, 82.311111111111202, 102.88888888888901, 102.88888888888901, 102.88888888888901, 102.88888888888901, 82.311111111111202],
    'VelEnd': [82.311111111111202, 102.88888888888901, 102.88888888888901, 102.88888888888901, 82.311111111111202, 102.88888888888901, 102.88888888888901, 102.88888888888901, 102.88888888888901, 82.311111111111202, 0],
    'TypeBeg': ['TAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS'],
    'TypeEnd': ['EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS', 'EAS']
}



def test_ATR42_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full ATR42 aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name='ATR42',
        aircraft=AIRCRAFT,
        mission=MISSION,
        saved='ATR42/outputs/OutputAircraft.mat',
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
