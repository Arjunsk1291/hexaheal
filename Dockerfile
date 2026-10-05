FROM ros:humble-ros-base
RUN apt-get update && apt-get install -y python3-pip ffmpeg libegl1 libgl1 libosmesa6 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
COPY . /work
RUN pip3 install -e ".[rl]" 
ENV MUJOCO_GL=egl
CMD ["bash","-lc","source /opt/ros/humble/setup.bash && cd ros2_ws && colcon build && source install/setup.bash && ros2 launch neurowalker_ros demo.launch.py controller:=tripod"]
