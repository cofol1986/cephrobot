import os
import subprocess
import sys
import time
# run test
if len(sys.argv) > 2 and sys.argv[2] == '--run-test':
    command = 'ceph -s | grep health | awk \'{print $2}\''
    while True:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        health_status, err = p.communicate()
        if health_status.strip() != "HEALTH_OK":
            time.sleep(5)
        else:
            break
    subprocess.call('ceph -s', shell=True)

    os.chdir(workspace_dir)
    test_script = config.get('performance test', 'script')
    shutil.copy(test_script, cluster_dir)
    #output_dir = config.get('performance test', 'output directory')
    output_dir = '%s/test_output' % cluster_dir
    #cephfs_mount_point = config.get('performance test', 'cephfs mount point')
    cephfs_mount_point = '/mnt/%s' % cluster

    # start to run test
    os.mkdir(output_dir)
    os.mkdir(cephfs_mount_point)

    all_nodes = map(lambda x:x[0:x.index(':')], osd_disks.split(' '))
    all_nodes.extend(mds_hosts.split(' '))
    all_nodes = {}.fromkeys(all_nodes).keys()
    file_object = open('%s/nodes' % output_dir, 'w')
    file_object.write('\n'.join(all_nodes))
    file_object.write('\nlocalhost\n')
    file_object.close()

    rc = subprocess.call('mount -t ceph %s:/ %s' % (first_mon_host, cephfs_mount_point), shell=True)
    if rc != 0:
        print 'Mounting cephfs failed.'
        sys.exit(1)

    test_script = os.path.abspath(test_script)
    output_dir = os.path.abspath(output_dir)
    os.chdir(cephfs_mount_point)
    command = 'source %s none %s/nodes | tee %s/%s.result' % (test_script, output_dir, output_dir, os.path.basename(test_script))
    rc = subprocess.call(command, shell=True)
    if rc != 0:
        print 'Running test failed.'
        sys.exit(1)
    #test_cmd = '%s none %s/nodes | tee %s/%s.result' % (test_script, output_dir, output_dir, os.path.basename(test_script))
    #pro = subprocess.Popen(test_cmd, stdout=subprocess.PIPE,
    #                       shell=True, preexec_fn=os.setsid)
    #os.killpg(pro.pid, signal.SIGTERM)

    # finish test, clean up, umount cephfs
    os.chdir(workspace_dir)
    subprocess.call('umount %s' % cephfs_mount_point, shell=True)
    os.rmdir(cephfs_mount_point)


