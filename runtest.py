#!/usr/bin/python
import os
import sys
import subprocess
import re
import cephrobot
import time


def runcmdtillend(command):
    """ run command till end"""
    cephrobot.printd(command)
    p = subprocess.Popen(command, shell=True)
    return p.wait()

def syncandclearcache():
    """sync and clear cache"""
    command = 'pssh -i -h hosts "sync && echo 3 > /proc/sys/vm/drop_caches"'
    runcmdtillend(command)

def runtest(fiocfgfile, resultdir):
    """run all testcases"""
    for cfgfile in fiocfgfile:
        #check the tc's type: read or write
        basename = os.path.basename(cfgfile)
        tctype = basename.split("_")[1][0]
        if tctype == 'r':
            #create test files
            command = 'RUNTIME=5 fio %s'%cfgfile
            runcmdtillend(command)

            #sync and drop the caches
            command = 'pssh -i -h hosts "sync && echo 3 > /proc/sys/vm/drop_caches"'
            runcmdtillend(command)

        #run the tc
        command = 'RUNTIME=60 fio %s'%cfgfile
        cephrobot.printd(command)
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        p.wait()
        output = p.communicate()[0]
        cephrobot.printd(output)


        #get the statistics
        #go the the cluster dir
        resultdir = os.path.abspath(resultdir)
        curdir = os.path.abspath(os.curdir)
        os.chdir(resultdir)

        #collect statistics
        print 'result dir is %s' % resultdir
        resultdetailfile = open("resultdetail", "a")
        resultdetailfile.write(output)
        resultdetailfile.close()
        tmpresultfile = open("tmpresult", "w+")
        tmpresultfile.write(output)
        tmpresultfile.close()

        bw=0
        iops=0
        lat=0
        re1 = re.compile(r'io=\d+.*bw=(\d+(\.\d+)?)(K|M)?B/s.*iops=(\d+).*runt=.*')
        re2 = re.compile(r'\blat\b.*\((.*)\).*avg=(\d+(\.\d+))?')
        with open("tmpresult", "r") as detailfile:
            for line in detailfile.readlines():
                if re1.search(line):
                    statistics = re1.search(line).groups()
                    if statistics[2] == 'K':
                        bw = float(statistics[0])
                    elif statistics[2] == 'M':
                        bw = float(statistics[0]) * 1024
                    elif statistics[2] is None:
                        bw = float(statistics) / 1024
                    iops = int(statistics[3])

                if re2.search(line):
                    statistics = re2.search(line).groups()
                    if statistics[0] == "msec":
                        lat = float(statistics[1])
                    else:
                        lat = float(statistics[1]) / 1000

        resultfile = open("result", "a")
        #if int(output[4]):
            #line = "#run status:error, return code is %s \n"%output[4]
        #else:
            #line = "#run status:ok \n"
        #resultfile.writelines(line)
        line =  basename + " " + str(bw)+ " " + str(iops) + " " + str(lat) + "\n"
        resultfile.writelines(line)
        resultfile.close()

        #rm test files
        command = r'rm -rf /mnt/*'
        runcmdtillend(command)
        os.chdir(curdir)
        syncandclearcache()


def checkcephstatus():
    #check ceph status
    command = "ceph health"
    p = subprocess.Popen(command, shell=True, stdout = subprocess.PIPE)
    p.wait()
    output = p.communicate()[0]
    if output.find("HEALTH_OK") == -1:
        cephrobot.printd("ERROR WITH CEPH STATUS")
        sys.exit(1)


tc_cfgfile = os.listdir(".")
tc_fiofile = [item for item in tc_cfgfile if re.search(r'.fio$', item)]
print(tc_fiofile)
tc_cfgfile = [item for item in tc_cfgfile if re.search(r'^tmplate', item)]
print(tc_cfgfile)

curdir = os.path.abspath(os.curdir)
for cfgfile in tc_cfgfile:
    try:
        cephrobot.printd("running tc %s"%cfgfile)
        robot=cephrobot.CephRobot(cfgfile)
        robot.launch_cluster()
        checkcephstatus()
        #mount /mnt
        command = "mount -t ceph 172.18.11.50:/ /mnt/"
        runcmdtillend(command)
        clusterdir = "cluster_%s"%os.path.basename(cfgfile)
        runtest(tc_fiofile, clusterdir)
    except Exception, e:
        cephrobot.printd("tc %s failed:%s"%( cfgfile, e ))
    finally:
        #umount /mnt
        os.chdir(curdir)
        command = "umount /mnt"
        runcmdtillend(command)
        robot.rm_cluster()
        cephrobot.printd("sleep 10s to do next tc")
        time.sleep(10)

