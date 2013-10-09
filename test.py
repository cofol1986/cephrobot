#/usr/bin/python

import cephrobot
robot=cephrobot.CephRobot(setting_file="tmplate")
robot.rm_cluster("ruijie-node0 ruijie-node1 ruijie-node2")
#robot.launch_cluster()
#robot.rm_cluster()
