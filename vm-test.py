# run vm test
if len(sys.argv) > 3 and sys.argv[3] == '--run-vm-test':
    normal_cephfs_mp = '/mnt/mycephfs'
    vm_name = 'win7.x64'
    rc = subprocess.call('mount -t ceph %s:/ %s' % (first_mon_host, normal_cephfs_mp), shell=True)
    if rc != 0:
        print 'Mounting cephfs failed.'
        sys.exit(1)

    command = 'mkdir %s/images' % normal_cephfs_mp
    rc = subprocess.call(command, shell=True)

    shutil.copy('/vmdata/testimages/win7.x64.img_autorun2', '%s/images/win7.x64.img' % normal_cephfs_mp)
    os.symlink(output_dir, '/test_output')

    shutil.copy('/vmdata/win7.x64.xml_ide', '/etc/libvirt/qemu/win7.x64.xml')
    command = 'service libvirtd restart'
    rc = subprocess.call(command, shell=True)

    command = 'virsh start %s' % vm_name
    rc = subprocess.call(command, shell=True)
    if rc != 0:
        print 'Starting vm failed.'
        sys.exit(1)

    while True:
        if os.path.exists('%s/win7_done' % output_dir):
            break
        time.sleep(5)

    time.sleep(5)

    command = 'virsh shutdown %s' % vm_name
    rc = subprocess.call(command, shell=True)
    if rc != 0:
        print 'Shutting down vm failed.'
        sys.exit(1)

    command = 'virsh list | grep "win7"'
    while True:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        win7_state, err = p.communicate()
        if win7_state.strip() != "":
            rc = subprocess.call('virsh shutdown %s' % vm_name, shell=True)
            time.sleep(5)
        else:
            break

    os.remove('%s/win7_done' % output_dir)

    shutil.copy('/vmdata/win7.x64.xml_virtio', '/etc/libvirt/qemu/win7.x64.xml')
    command = 'service libvirtd restart'
    rc = subprocess.call(command, shell=True)

    command = 'virsh start %s' % vm_name
    rc = subprocess.call(command, shell=True)
    if rc != 0:
        print 'Starting vm failed.'
        sys.exit(1)

    while True:
        if os.path.exists('%s/win7_done' % output_dir):
            break
        time.sleep(5)

    time.sleep(5)

    command = 'virsh shutdown %s' % vm_name
    rc = subprocess.call(command, shell=True)
    if rc != 0:
        print 'Shutting down vm failed.'
        sys.exit(1)

    command = 'virsh list | grep "win7"'
    while True:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        win7_state, err = p.communicate()
        if win7_state.strip() != "":
            rc = subprocess.call('virsh shutdown %s' % vm_name, shell=True)
            time.sleep(5)
        else:
            break

    os.remove('/test_output')

    command = '/root/clearcache'
    rc = subprocess.call(command, shell=True)

    subprocess.call('umount %s' % normal_cephfs_mp, shell=True)


