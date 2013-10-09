import os
import sys
import time
import re
import shutil
import subprocess
import ConfigParser
def printd(str):
    """print decorated str"""
    print("******************************")
    print(str)
    print("******************************")
class CephRobot:
    """CephRobot is designed to do testcase automately"""
    def __init__(self, setting_file="test.setting", clear_or_not=True):
        """setting tmplate file and other args"""
        self.setting_file = setting_file
        self.clear_or_not = clear_or_not
        self.hostfile="hosts"


        #init config_parser
        self.config_parser = ConfigParser.ConfigParser()
        readfiles = self.config_parser.read(self.setting_file)
        if not readfiles:
            print( "error while parsing %s"%self.setting_file )

        #cluster
        self.cluster_dir=""
        self.workspace_dir = os.path.abspath(os.curdir)
        self.mon_hosts = ""


    def launch_cluster(self):
        """create new cluster """
        #cluster_dir = self.config_parser.get('creation params', 'cluster directory')
        cluster = os.path.basename(self.setting_file)
        self.cluster_dir = 'cluster_%s' % cluster
        printd("creating dir %s"%self.cluster_dir)
        if os.path.exists(self.cluster_dir):
            print 'The cluster dir "%s" already exists. remove it now.' % self.cluster_dir
            subprocess.check_call([ "rm","-rf", self.cluster_dir ])

        os.mkdir(self.cluster_dir)
        printd("copy file %s to dir %s"%(self.setting_file, self.cluster_dir))
        shutil.copy(self.setting_file, self.cluster_dir)
        shutil.copy(self.hostfile, self.cluster_dir)
        printd("chdir to %s"%self.cluster_dir)
        os.chdir(self.cluster_dir)

        # launch cluster as defined
        mon_hosts = self.config_parser.get('creation params', 'mon host')
        self.mon_hosts = mon_hosts
        printd("self.mon_hosts %s"%self.mon_hosts)
        if len(mon_hosts.split(' ')) <= 0:
            print "Please specify one or more monitors."

        command = 'ceph-deploy new %s' % mon_hosts
        printd("running %s"%command)
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            print 'Creating cluster failed.'
            sys.exit(1)

        printd("dealing with new config file")
        new_config_parser = ConfigParser.ConfigParser()
        new_config_parser.readfp(open('./ceph.conf'))
        try:
            new_config_parser.remove_option('global', 'auth supported')
        except:
            #print 'No auth supported option'
            pass

        all_cluster_settings = self.config_parser.items('ceph cluster settings')
        for setting in all_cluster_settings:
            try:
                new_config_parser.set('global', setting[0], setting[1])
            except:
                print "Setting ceph.conf failed."
                sys.exit(1)

        #write mon/osd/mds config
        for sec in self.config_parser.sections():
            if re.search(r'^(mon|mds|osd)(.\d+)?$', sec):
                new_config_parser.add_section(sec)
                items = self.config_parser.items(sec)
                for item in items:
                    try:
                        new_config_parser.set(sec, item[0], item[1])
                    except:
                        print "Setting ceph.conf failed."
                        sys.exit(1)

        with open('./ceph.conf', 'wb') as configfile:
            new_config_parser.write(configfile)
        command = 'ceph-deploy mon create %s' % mon_hosts
        printd("running %s"%command)
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            print 'Creating mons failed.'
            sys.exit(1)

        printd("sleep 20s")
        time.sleep(20)
        first_mon_host = mon_hosts.split(' ')[0]
        command = 'ceph-deploy gatherkeys %s' % first_mon_host
        printd("run %s"%command)
        while True:
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                time.sleep(5)
            else:
                break

        zap_disks = self.config_parser.get('creation params', 'zap disk')
        command = 'ceph-deploy disk zap %s' % zap_disks
        printd("run %s"%command)
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            print 'Zapping disks failed.'
            sys.exit(1)

        osd_disks = self.config_parser.get('creation params', 'osd disk')
        command = 'ceph-deploy osd create %s' % osd_disks
        printd("run %s"%command)
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            print 'Creating osds failed.'
            sys.exit(1)

        # set CRUSH map for 1 node or 2 nodes cluster
        node_num = len({}.fromkeys(map(lambda x:x[0:x.index(':')], osd_disks.split(' '))).keys())
        if node_num <= 2:
            printd("alert!! node num is %d"%node_num)
            command = 'ceph osd getcrushmap -o old_coded_map'
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Getting crush map failed.'
                sys.exit(1)
            command = 'crushtool -d old_coded_map -o old_decoded_map'
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Decoding crush map failed.'
                sys.exit(1)
            command = 'cat old_decoded_map | sed "s/type host/type osd/g" | tee new_decoded_map'
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            command = 'crushtool -c new_decoded_map -o new_coded_map'
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Coding crush map failed.'
                sys.exit(1)
            command = 'ceph osd setcrushmap -i new_coded_map'
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Setting crush map failed.'
                sys.exit(1)

        command = 'ceph -s | grep health | awk \'{print $2}\''
        printd("run %s"%command)
        count = 3
        while count > 1:
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            health_status, err = p.communicate()
            if health_status.strip() != "HEALTH_OK":
                printd("Alert !!! ceph status is not health")
                time.sleep(5)
                count = count - 1
            else:
                break
        if count < 1:
            printd("ceph status is not health within 15s,quit....")
            sys.exit(1)
        subprocess.call('ceph -s', shell=True)

        mds_hosts = self.config_parser.get('creation params', 'mds host')
        command = 'ceph-deploy mds create %s' % mds_hosts
        printd("run %s"%command)
        rc = subprocess.call(command, shell=True)
        if rc != 0:
            print 'Creating mds failed.'
            sys.exit(1)

        # set cephfs data and metadata pools
        keep_no_change = False
        try:
            keep_no_change = self.config_parser.getboolean('cephfs settings', 'keep no change')
        except:
            pass

        if not keep_no_change:
            printd("keep no change is False")
            osd_num = len(osd_disks.split(' '))
            data_pool_name = self.config_parser.get('cephfs settings', 'data pool name')
            if data_pool_name == 'data':
                print "Don't use the default name."
                sys.exit(1)
            data_pool_replica_size = int(self.config_parser.get('cephfs settings', 'data pool replica size'))
            if data_pool_replica_size <= 0:
                print "Please specify a number bigger than 0."
            try:
                data_placement_group_number = int(self.config_parser.get('cephfs settings', 'data placement group number'))
            except:
                #print 'No data placement group number option'
                data_placement_group_number = (100 * osd_num)/data_pool_replica_size

            metadata_pool_name = self.config_parser.get('cephfs settings', 'metadata pool name')
            if metadata_pool_name == 'metadata':
                print "Don't use the default name."
                sys.exit(1)
            metadata_pool_replica_size = int(self.config_parser.get('cephfs settings', 'metadata pool replica size'))
            if metadata_pool_replica_size <= 0:
                print "Please specify a number bigger than 0."
            try:
                metadata_placement_group_number = int(self.config_parser.get('cephfs settings', 'metadata placement group number'))
            except:
                #print 'No metadata placement group number option'
                metadata_placement_group_number = (100 * osd_num)/metadata_pool_replica_size

            command = 'ceph osd pool create %s %s %s' % (data_pool_name, data_placement_group_number, data_placement_group_number)
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Creating data pool failed.'
                sys.exit(1)
            command = 'ceph osd pool set %s size %s' % (data_pool_name, data_pool_replica_size)
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Setting data replica size failed.'
                sys.exit(1)
            command = 'ceph osd pool create %s %s %s' % (metadata_pool_name, metadata_placement_group_number, metadata_placement_group_number)
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Creating metadata pool failed.'
                sys.exit(1)
            command = 'ceph osd pool set %s size %s' % (metadata_pool_name, metadata_pool_replica_size)
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Setting metadata replica size failed.'
                sys.exit(1)
            rc = subprocess.call('ceph osd pool set %s crush_ruleset 1' % metadata_pool_name, shell=True)
            if rc != 0:
                print 'Setting metadata rule set failed.'
                sys.exit(1)

            command = 'ceph osd dump | grep "^pool" | grep "%s" | awk \'{print $2}\'' % data_pool_name
            printd("run %s"%command)
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            data_pool_id, err = p.communicate()
            command = 'ceph osd dump | grep "^pool" | grep "%s" | awk \'{print $2}\'' % metadata_pool_name
            printd("run %s"%command)
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            metadata_pool_id, err = p.communicate()
            command = 'ceph mds newfs %s %s --yes-i-really-mean-it' % (int(metadata_pool_id), int(data_pool_id))
            printd("run %s"%command)
            rc = subprocess.call(command, shell=True)
            if rc != 0:
                print 'Renewing cephfs failed.'
                sys.exit(1)
        time.sleep(2)
        subprocess.call('ceph -s', shell=True)
        os.chdir(self.workspace_dir)

    def rm_cluster(self):
        hostnames = self.config_parser.get('rm cluster', 'host names')
        hostnames = hostnames.split(" ")
        if  not hostnames:
            print "no mon hosts find ... ..."
            exit(1)

        if self.clear_or_not:
            rm_dir = "rm_dir"
            if os.path.exists(rm_dir):
                printd("deleting %s"%rm_dir)
                subprocess.check_call([ "rm","-rf",rm_dir ])

            printd("copying files ....")
            os.mkdir(rm_dir)
            shutil.copy("./rm-ceph-cluster", rm_dir)
            shutil.copy("./rm-ceph-local", rm_dir)
            os.chdir(rm_dir)
            subprocess.check_call([ "chmod","a+x","rm-ceph-cluster" ])
            subprocess.check_call([ "chmod","a+x","rm-ceph-local" ])
            try:
                command = [ "./rm-ceph-cluster" ] + hostnames
                printd("running %s"%command)
                subprocess.check_call(command)
            except subprocess.CalledProcessError:
                print("error while rm ceph_cluster")
                sys.exit(1)
        os.chdir(self.workspace_dir)
