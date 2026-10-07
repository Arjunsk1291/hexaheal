from setuptools import find_packages, setup

package_name = "neurowalker_ros"
setup(
    name=package_name, version="0.1.0", packages=find_packages(),
    data_files=[("share/ament_index/resource_index/packages", ["resource/" + package_name]),
                ("share/" + package_name, ["package.xml"]),
                ("share/" + package_name + "/launch", ["launch/demo.launch.py"])],
    install_requires=["setuptools"], zip_safe=True, maintainer="Arjun Sunil Kumar", license="MIT",
    entry_points={"console_scripts": [f"{n} = neurowalker_ros.nodes:{n}_main" for n in
                  ["sim_node", "brain_node", "gait_node", "health_monitor_node", "decision_node", "metrics_logger"]]},
)
