"""ros2 launch neurowalker_ros demo.launch.py controller:=tripod|connectome  (UNVERIFIED)"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    ctrl = LaunchConfiguration("controller")
    nodes = [DeclareLaunchArgument("controller", default_value="tripod"), DeclareLaunchArgument("terrain", default_value="flat"),
             Node(package="neurowalker_ros", executable="sim_node", parameters=[{"terrain": LaunchConfiguration("terrain")}]),
             Node(package="neurowalker_ros", executable="gait_node"),
             Node(package="neurowalker_ros", executable="brain_node", condition=IfCondition(PythonExpression(["'", ctrl, "' == 'connectome'"]))),
             Node(package="neurowalker_ros", executable="health_monitor_node"),
             Node(package="neurowalker_ros", executable="decision_node"),
             Node(package="neurowalker_ros", executable="metrics_logger"),
             ExecuteProcess(cmd=["ros2", "bag", "record", "-o", "neurowalker_bag", "/joint_states", "/imu", "/contacts", "/joint_commands", "/decision"], output="screen")]
    return LaunchDescription(nodes)
