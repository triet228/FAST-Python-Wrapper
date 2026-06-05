# tests/test_AEA.py

"""Run the AEA fixture through Python dictionaries and compare FAST output."""

from wrapper import MatlabRow as row, matlab_expr as m

nan = float("nan")

from tests.helpers import (
    assert_fast_model_wrapper_matches_saved_output,
    fast_models_path,
    fast_path,
)


GRAPH_BASED_PROPULSION = {
    'Arch': [
        [0, 1, 1, 1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ],
    'OperUps': m('@()[0,1,1,1,1,0,0,0,0,0;0,0,0,0,0,1,0,0,0,0;0,0,0,0,0,0,1,0,0,0;0,0,0,0,0,0,0,1,0,0;0,0,0,0,0,0,0,0,1,0;0,0,0,0,0,0,0,0,0,1;0,0,0,0,0,0,0,0,0,1;0,0,0,0,0,0,0,0,0,1;0,0,0,0,0,0,0,0,0,1;0,0,0,0,0,0,0,0,0,0]'),
    'OperDwn': m('@()[0,0,0,0,0,0,0,0,0,0;1,0,0,0,0,0,0,0,0,0;1,0,0,0,0,0,0,0,0,0;1,0,0,0,0,0,0,0,0,0;1,0,0,0,0,0,0,0,0,0;0,1,0,0,0,0,0,0,0,0;0,0,1,0,0,0,0,0,0,0;0,0,0,1,0,0,0,0,0,0;0,0,0,0,1,0,0,0,0,0;0,0,0,0,0,0.25,0.25,0.25,0.25,0]'),
    'EtaUps': [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 0.66100000000000003, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 0.66100000000000003, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 0.66100000000000003, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 0.66100000000000003, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    'EtaDwn': [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0.66100000000000003, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 0.66100000000000003, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 0.66100000000000003, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 0.66100000000000003, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    'SrcType': 0,
    'TrnType': row([0, 0, 0, 0, 2, 2, 2, 2])
}

AIRCRAFT = {
    'Specs': {
        'TLAR': {
            'EIS': 2016,
            'Class': 'Turbofan',
            'MaxPax': 185.1157894736842
        },
        'Performance': {
            'Vels': {
                'Tko': 69.450000000000074,
                'Crs': 0.747,
                'Type': 'TAS'
            },
            'Alts': {
                'Tko': 0,
                'Crs': 7829
            },
            'Range': 926000,
            'RCMax': 10.160000000000002
        },
        'Aero': {
            'L_D': {
                'Clb': 16,
                'Crs': 18.600000000000001,
                'Des': 16
            },
            'W_S': {
                'SLS': 871.81528662420385
            }
        },
        'Weight': {
            'MTOW': 109500,
            'EG': nan,
            'EM': nan,
            'Fuel': 0,
            'Batt': 36000,
            'WairfCF': 0.87
        },
        'Propulsion': {
            'PropArch': 'O',
            'PropArchGraph': GRAPH_BASED_PROPULSION,
            'Engine': nan,
            'NumEngines': 4,
            'T_W': {
                'SLS': 0.29999999999999999
            },
            'Thrust': {
                'SLS': nan
            },
            'Eta': {
                'Prop': 0.80000000000000004
            }
        },
        'Power': {
            'SpecEnergy': {
                'Fuel': 12,
                'Batt': 0.55999999999999994
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
            'Battery': {
                'ParCells': nan,
                'SerCells': nan,
                'BegSOC': 100
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
        'Table': 0,
        'VisualizeAircraft': 0,
        'Offtake': 0
    }
}

MISSION = {
    'Target': {
        'Valu': 926000,
        'Type': 'Dist'
    },
    'Segs': ['Takeoff', 'Climb', 'Cruise', 'Descent'],
    'ID': [1, 1, 1, 1],
    'AltBeg': [0, 0, 7829, 7829],
    'AltEnd': [0, 7829, 7829, 0],
    'ClbRate': [nan, nan, nan, nan],
    'VelBeg': [0, 69.450000000000074, 0.747, 0.747],
    'VelEnd': [69.450000000000074, 0.747, 0.747, 83.340000000000089],
    'TypeBeg': ['TAS', 'TAS', 'Mach', 'Mach'],
    'TypeEnd': ['TAS', 'Mach', 'Mach', 'TAS']
}



def test_AEA_wrapper_output_matches_saved_mat_file(
    fast_path,
    fast_models_path,
    tmp_path,
):
    """Check the full AEA aircraft output against saved OutputAircraft.mat."""

    assert_fast_model_wrapper_matches_saved_output(
        name='AEA',
        aircraft=AIRCRAFT,
        mission=MISSION,
        saved='AEA/outputs/OutputAircraft.mat',
        fast_path=fast_path,
        fast_models_path=fast_models_path,
        tmp_path=tmp_path,
    )
