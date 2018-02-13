import random
import logging
import string
import os
import inspect
from shutit_module import ShutItModule

class shutit_kubernetes(ShutItModule):


	def build(self, shutit):
		shutit.run_script('''#!/bin/bash
MODULE_NAME=shutit_kubernetes
rm -rf $( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/vagrant_run/*
if [[ $(command -v VBoxManage) != '' ]]
then
	while true
	do
		VBoxManage list runningvms | grep ${MODULE_NAME} | awk '{print $1}' | xargs -IXXX VBoxManage controlvm 'XXX' poweroff && VBoxManage list vms | grep shutit_kubernetes | awk '{print $1}'  | xargs -IXXX VBoxManage unregistervm 'XXX' --delete
		# The xargs removes whitespace
		if [[ $(VBoxManage list vms | grep ${MODULE_NAME} | wc -l | xargs) -eq '0' ]]
		then
			break
		else
			ps -ef | grep virtualbox | grep ${MODULE_NAME} | awk '{print $2}' | xargs kill
			sleep 10
		fi
	done
fi
if [[ $(command -v virsh) ]] && [[ $(kvm-ok 2>&1 | command grep 'can be used') != '' ]]
then
	virsh list | grep ${MODULE_NAME} | awk '{print $1}' | xargs -n1 virsh destroy
fi
''')
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		gui = shutit.cfg[self.module_id]['gui']
		memory = shutit.cfg[self.module_id]['memory']
		shutit.build['vagrant_run_dir'] = os.path.dirname(os.path.abspath(inspect.getsourcefile(lambda:0))) + '/vagrant_run'
		shutit.build['module_name'] = 'shutit_kubernetes_' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.build['this_vagrant_run_dir'] = shutit.build['vagrant_run_dir'] + '/' + shutit.build['module_name']
		shutit.send(' command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		shutit.send('command rm -rf ' + shutit.build['this_vagrant_run_dir'] + ' && command mkdir -p ' + shutit.build['this_vagrant_run_dir'] + ' && command cd ' + shutit.build['this_vagrant_run_dir'])
		if shutit.send_and_get_output('vagrant plugin list | grep landrush') == '':
			shutit.send('vagrant plugin install landrush')
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send_file(shutit.build['this_vagrant_run_dir'] + '/Vagrantfile','''Vagrant.configure("2") do |config|
  config.landrush.enabled = true
  config.vm.provider "virtualbox" do |vb|
    vb.gui = ''' + gui + '''
    vb.memory = "''' + memory + '''"
  end

  config.vm.define "kubernetes1" do |kubernetes1|
    kubernetes1.vm.box = ''' + '"' + vagrant_image + '"' + '''
    kubernetes1.vm.hostname = "kubernetes1.vagrant.test"
    config.vm.provider :virtualbox do |vb|
      vb.name = "shutit_kubernetes_1"
    end
  end
end''')
		try:
			pw = file('secret').read().strip()
		except IOError:
			pw = ''
		if pw == '':
			shutit.log('''================================================================================\nWARNING! IF THIS DOES NOT WORK YOU MAY NEED TO SET UP A 'secret' FILE IN THIS FOLDER!\n================================================================================''',level=logging.CRITICAL)
			pw='nopass'
		try:
			shutit.multisend('vagrant up --provider ' + shutit.cfg['shutit-library.virtualization.virtualization.virtualization']['virt_method'] + " kubernetes1",{'assword for':pw,'assword:':pw},timeout=99999)
		except NameError:
			shutit.multisend('vagrant up kubernetes1',{'assword for':pw,'assword:':pw},timeout=99999)
		if shutit.send_and_get_output("""vagrant status | grep -w ^kubernetes1 | awk '{print $2}'""") != 'running':
			shutit.pause_point("machine: kubernetes1 appears not to have come up cleanly")


		# machines is a dict of dicts containing information about each machine for you to use.
		machines = {}
		machines.update({'kubernetes1':{'fqdn':'kubernetes1.vagrant.test'}})
		ip = shutit.send_and_get_output('''vagrant landrush ls 2> /dev/null | grep -w ^''' + machines['kubernetes1']['fqdn'] + ''' | awk '{print $2}' ''')
		machines.get('kubernetes1').update({'ip':ip})


		for machine in sorted(machines.keys()):
			shutit.login(command='vagrant ssh ' + machine,check_sudo=False)
			shutit.login(command='sudo su -',password='vagrant',check_sudo=False)
			# Workaround for docker networking issues + landrush.
			shutit.install('docker')
			shutit.insert_text('Environment=GODEBUG=netdns=cgo','/lib/systemd/system/docker.service',pattern='.Service.')
			shutit.send('mkdir -p /etc/docker',note='Create the docker config folder')
			shutit.send_file('/etc/docker/daemon.json',"""{
  "dns": ["8.8.8.8"]
}""",note='Use the google dns server rather than the vagrant one. Change to the value you want if this does not work, eg if google dns is blocked.')
			shutit.send('systemctl daemon-reload && systemctl restart docker')
			shutit.logout()
			shutit.logout()
		shutit.login(command='vagrant ssh ' + sorted(machines.keys())[0],check_sudo=False)
		shutit.login(command='sudo su -',password='vagrant',check_sudo=False)
		shutit.run_script('''ETCD_VER=v3.3.0
# choose either URL
GOOGLE_URL=https://storage.googleapis.com/etcd
GITHUB_URL=https://github.com/coreos/etcd/releases/download
DOWNLOAD_URL=${GOOGLE_URL}
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-download-test && mkdir -p /tmp/etcd-download-test

curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-download-test --strip-components=1
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

/tmp/etcd-download-test/etcd --version
<<COMMENT
etcd Version: 3.3.0
Git SHA: c23606781
Go Version: go1.9.3
Go OS/Arch: linux/amd64
COMMENT

ETCDCTL_API=3 /tmp/etcd-download-test/etcdctl version
<<COMMENT
etcdctl version: 3.3.0
API version: 3.3
COMMENT''')
		shutit.send('export PATH=${PATH}:/tmp/etcd-download-test')
		shutit.multisend('add-apt-repository ppa:gophers/archive',{'ENTER':''})
		shutit.send('apt-get update')
		shutit.install('golang-1.9-go')
		shutit.install('openssl')
		shutit.install('libfuse-dev')
		shutit.install('libjson-c-dev')
		shutit.install('apt-file')
		shutit.send('apt-file update')
		shutit.send('export GOROOT=/usr/lib/go-1.9')
		shutit.send('export GOPATH=/usr/lib/go-1.9/bin')
		shutit.send('export PATH=${PATH}:/usr/lib/go-1.9/bin')
		shutit.send('go get -u github.com/cloudflare/cfssl/cmd/...')
		shutit.send('git clone https://github.com/adelton/kubernetes-flexvolume-fuse')
		# Flexvolume setup
		shutit.send('cd /root/kubernetes-flexvolume-fuse')
		shutit.send('mkdir -p /usr/libexec/kubernetes/kubelet-plugins/volume/exec/example.com~pod-info-fuse')
		shutit.send('mkdir -p mkdir -p /usr/libexec/kubernetes/kubelet-plugins/volume/exec/example.com~custodia-cli-fuse')
		shutit.send('gcc -Wall flexvolume-fuse-external.c $( pkg-config fuse json-c --cflags --libs )       -D LOG_FILE=/tmp/custodia-cli.log       -o /usr/libexec/kubernetes/kubelet-plugins/volume/exec/example.com~custodia-cli-fuse/custodia-cli-fuse')
		shutit.send('gcc -Wall pod-info-fuse.c $( pkg-config fuse json-c --cflags --libs )       -D LOG_FILE=/tmp/pod-info.log       -o /usr/libexec/kubernetes/kubelet-plugins/volume/exec/example.com~pod-info-fuse/pod-info-fuse')
		# Kubernetes setup
		shutit.send('cd /root')
		shutit.send('git clone --depth=1 https://github.com/kubernetes/kubernetes.git')
		shutit.send('cd /root/kubernetes')
		shutit.send('nohup ./hack/local-up-cluster.sh 2>&1 | tee /tmp/buildout &')
		shutit.send('export PATH=${PATH}:$(pwd)/_output/local/bin/linux/amd64')
		shutit.send_until('kubectl get nodes','NAME')
		shutit.send_file('/root/pod.yaml','''apiVersion: v1
kind: Pod
metadata:
  name: test-pod-hashicorp
spec:
  containers:
  - image: registry.access.redhat.com/rhel7
    name: test-pod-hashicorp
    command: ["/usr/bin/sleep"]
    args: ["infinity"]
    volumeMounts:
    - mountPath: /mnt/hashicorp
      name: hashicorp-cli
  volumes:
  - flexVolume:
      driver: example.com/hashicorp-cli-fuse
    name: hashicorp-cli''')
		shutit.send('kubectl create -f /root/pod.yaml')
		shutit.pause_point('')
		shutit.logout()
		shutit.logout()
		shutit.log('''Vagrantfile created in: ''' + shutit.build['this_vagrant_run_dir'],add_final_message=True,level=logging.DEBUG)
		shutit.log('''Run:

	cd ''' + shutit.build['this_vagrant_run_dir'] + ''' && vagrant status && vagrant landrush ls

To get a picture of what has been set up.''',add_final_message=True,level=logging.DEBUG)
		return True


	def get_config(self, shutit):
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/xenial64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'gui',default='false')
		shutit.get_config(self.module_id,'memory',default='4096')
		return True

	def test(self, shutit):
		return True

	def finalize(self, shutit):
		return True

	def is_installed(self, shutit):
		return False

	def start(self, shutit):
		return True

	def stop(self, shutit):
		return True

def module():
	return shutit_kubernetes(
		'git.shutit_kubernetes.shutit_kubernetes', 2119562175.0001,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualization.virtualization.virtualization','tk.shutit.vagrant.vagrant.vagrant']
	)
