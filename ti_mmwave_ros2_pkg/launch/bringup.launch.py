import os

import launch
from launch import LaunchDescription
from launch_ros.actions import Node

from launch.actions import TimerAction, RegisterEventHandler

from launch.event_handlers import OnProcessExit
from launch_ros.descriptions import ComposableNode
from launch_ros.actions import ComposableNodeContainer

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    cfg_file = "iwr1843boost_outdoor_hires_10m.cfg"  #"iwr1843boost_outdoor_survey_hover.cfg"
    cfg_file = "iwr1843boost_outdoor_survey_hover.cfg"
    #cfg_file = "iwr1843boost_outdoor_survey_25m_576k.cfg"
    #cfg_file = "iwr1843boost_config4_max_fov_no_clutter.cfg"
    #cfg_file = "iwr1843boost_outdoor_survey_25m_final.cfg"

    pkg_dir_path = get_package_share_directory('ti_mmwave_ros2_pkg')
    cfg_file_path = os.path.join(pkg_dir_path, 'cfg', cfg_file)
    rviz_config_file = os.path.join(pkg_dir_path, 'rviz', 'mmwave_3d_view.rviz')

    mmwave_quick_config = Node(
        package='ti_mmwave_ros2_pkg',
        executable='mmWaveQuickConfig',
        name='mmwave_quick_config',
        output='screen',
        arguments=[cfg_file_path],
        parameters=[{
            "mmWaveCLI_name": "/mmWaveCLI",
        }],
    )

    # Physics parameters are derived from the cfg by ParameterParser at runtime
    # and overwrite these values. They are set here explicitly so the node starts
    # with correct values for this config rather than stale hardcoded defaults.
    #
    # Derived from iwr1843boost_outdoor_survey_hover.cfg using ParameterParser formulas:
    #   profileCfg: startFreq=77GHz, idleTime=30µs, rampEnd=35µs,
    #               freqSlope=45MHz/µs, numAdcSamples=128, adcSamplingFreq=10000ksps
    #   frameCfg:   numLoops=128, framePeriodicity=66.66ms, chirpIdx 0-2 → 3 TX
    #
    #   fs   = 10000e3 = 10.0 MHz
    #   adc_duration = 128 / 10e6 = 12.8 µs
    #   BW   = 45e12 * 12.8e-6 = 576.0 MHz
    #   PRI  = (30+35)*1e-6 = 65.0 µs  (one full TX cycle, TDM MIMO slot)
    #   fc   = 77e9 + 45e12*(7e-6 + 6.4e-6) = 77.000603 GHz
    #   vrange     = c/(2*BW)       = 299792458/(2*576e6) = 0.2602 m
    #   max_range  = 128 * 0.2602   = 33.31 m  (ADC limit; CFAR caps to 25m)
    #   max_vel    = c/(2*fc*PRI)/ntx = 299792458/(2*77.000603e9*65e-6)/3 = 9.983 m/s
    #   vvel       = max_vel/128    = 0.07799 m/s
    mmwave_comm_srv_node = Node(
        package='ti_mmwave_ros2_pkg',
        executable='mmwave_comm_srv_node',
        name='mmWaveCommSrvNode',
        output='screen',
        parameters=[{
            "command_port": "/dev/iwr1843_cfg",
            "command_rate": 115200,
            "mmWaveCLI_name": "/mmWaveCLI",
            # radar parameters
            "numAdcSamples": 128,
            "numLoops": 128,
            "num_TX": 3,
            "f_s": 10000000.0,
            "f_c": 77000603000.0,
            "BW": 576000000.0,
            "PRI": 0.000065,
            "t_fr": 0.06666,
            "max_range": 33.31,
            "range_resolution": 0.2602,
            "max_doppler_vel": 9.983,
            "doppler_vel_resolution": 0.07799,
        }],
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': False}],
    )

    """Generate launch description with multiple components."""
    container = ComposableNodeContainer(
            name='my_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[
                ComposableNode(
                    package='ti_mmwave_ros2_pkg',
                    plugin='ti_mmwave_ros2_pkg::mmWaveDataHdl',
                    name='mmWaveDataHdl',
                    parameters=[{
                        "data_port": "/dev/iwr1843_data",
                        "data_rate": 921600,
                        "frame_id": "ti_mmwave_0",
                        "max_allowed_elevation_angle_deg": 15,  # aoaFovCfg: ±15°
                        "max_allowed_azimuth_angle_deg": 60,    # aoaFovCfg: ±60°
                    }]
                ),
            ],
            output='screen',
    )

    return launch.LaunchDescription([
        mmwave_comm_srv_node,
        mmwave_quick_config,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=mmwave_quick_config,
                on_exit=[container],
            )
        ),
    ])
