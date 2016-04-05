"""ShutIt module. See http://shutit.tk
"""

from shutit_module import ShutItModule
import random
import string

class shutit_kubernetes(ShutItModule):

	def build(self, shutit):
		# Some useful API calls for reference. See shutit's docs for more info and options:
		#
		# ISSUING BASH COMMANDS
		# shutit.send(send,expect=<default>) - Send a command, wait for expect (string or compiled regexp)
		#                                      to be seen before continuing. By default this is managed
		#                                      by ShutIt with shell prompts.
		# shutit.multisend(send,send_dict)   - Send a command, dict contains {expect1:response1,expect2:response2,...}
		# shutit.send_and_get_output(send)   - Returns the output of the sent command
		# shutit.send_and_match_output(send, matches)
		#                                    - Returns True if any lines in output match any of
		#                                      the regexp strings in the matches list
		# shutit.send_until(send,regexps)    - Send command over and over until one of the regexps seen in the output.
		# shutit.run_script(script)          - Run the passed-in string as a script
		# shutit.install(package)            - Install a package
		# shutit.remove(package)             - Remove a package
		# shutit.login(user='root', command='su -')
		#                                    - Log user in with given command, and set up prompt and expects.
		#                                      Use this if your env (or more specifically, prompt) changes at all,
		#                                      eg reboot, bash, ssh
		# shutit.logout(command='exit')      - Clean up from a login.
		#
		# COMMAND HELPER FUNCTIONS
		# shutit.add_to_bashrc(line)         - Add a line to bashrc
		# shutit.get_url(fname, locations)   - Get a file via url from locations specified in a list
		# shutit.get_ip_address()            - Returns the ip address of the target
		# shutit.command_available(command)  - Returns true if the command is available to run
		#
		# LOGGING AND DEBUG
		# shutit.log(msg,add_final_message=False) -
		#                                      Send a message to the log. add_final_message adds message to
		#                                      output at end of build
		# shutit.pause_point(msg='')         - Give control of the terminal to the user
		# shutit.step_through(msg='')        - Give control to the user and allow them to step through commands
		#
		# SENDING FILES/TEXT
		# shutit.send_file(path, contents)   - Send file to path on target with given contents as a string
		# shutit.send_host_file(path, hostfilepath)
		#                                    - Send file from host machine to path on the target
		# shutit.send_host_dir(path, hostfilepath)
		#                                    - Send directory and contents to path on the target
		# shutit.insert_text(text, fname, pattern)
		#                                    - Insert text into file fname after the first occurrence of
		#                                      regexp pattern.
		# shutit.delete_text(text, fname, pattern)
		#                                    - Delete text from file fname after the first occurrence of
		#                                      regexp pattern.
		# shutit.replace_text(text, fname, pattern)
		#                                    - Replace text from file fname after the first occurrence of
		#                                      regexp pattern.
		# ENVIRONMENT QUERYING
		# shutit.host_file_exists(filename, directory=False)
		#                                    - Returns True if file exists on host
		# shutit.file_exists(filename, directory=False)
		#                                    - Returns True if file exists on target
		# shutit.user_exists(user)           - Returns True if the user exists on the target
		# shutit.package_installed(package)  - Returns True if the package exists on the target
		# shutit.set_password(password, user='')
		#                                    - Set password for a given user on target
		#
		# USER INTERACTION
		# shutit.get_input(msg,default,valid[],boolean?,ispass?)
		#                                    - Get input from user and return output
		# shutit.fail(msg)                   - Fail the program and exit with status 1
		#
		vagrant_image = shutit.cfg[self.module_id]['vagrant_image']
		vagrant_provider = shutit.cfg[self.module_id]['vagrant_provider']
		module_name = 'shutit_kubernetes' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
		shutit.send('rm -rf /tmp/' + module_name + ' && mkdir -p /tmp/' + module_name + ' && cd /tmp/' + module_name)
		shutit.send('vagrant init ' + vagrant_image)
		shutit.send('vagrant up --provider virtualbox',timeout=99999)
		shutit.login(command='vagrant ssh')
		shutit.login(command='sudo su -',password='vagrant')
		shutit.send('apt-get update')
		#http://kubernetes.io/docs/getting-started-guides/docker/
		shutit.install('docker.io')
		shutit.send('export K8S_VERSION=' + shutit.cfg[self.module_id]['kubernetes_version'])
		shutit.send('''docker run --volume=/:/rootfs:ro --volume=/sys:/sys:ro --volume=/var/lib/docker/:/var/lib/docker:rw --volume=/var/lib/kubelet/:/var/lib/kubelet:rw --volume=/var/run:/var/run:rw --net=host --pid=host --privileged=true --name=kubelet -d gcr.io/google_containers/hyperkube-amd64:v${K8S_VERSION} /hyperkube kubelet --containerized --hostname-override="127.0.0.1" --address="0.0.0.0" --api-servers=http://localhost:8080 --config=/etc/kubernetes/manifests --cluster-dns=10.0.0.10 --cluster-domain=cluster.local --allow-privileged=true --v=2''',note='Start the hyperkube docker image as a kubelet.')
		shutit.send('wget http://storage.googleapis.com/kubernetes-release/release/v${K8S_VERSION}/bin/linux/amd64/kubectl')
		shutit.send('chmod +x kubectl')
		shutit.send('export PATH=$PATH:$(pwd)')
		shutit.send('kubectl version',check_exit=False)
		shutit.send_until('kubectl get pods','.*Running.*',note='Wait until the pods are started up')
		shutit.send('docker run -d --net=host --privileged gcr.io/google_containers/hyperkube:v0.14.1 /hyperkube proxy --master=http://127.0.0.1:8080 --v=2',note='Start the hyperkube proxy')
		shutit.send('kubectl -s http://localhost:8080 run-container todopod --image=dockerinpractice/todo --port=8000',note='Start up a simple todo app')
		shutit.send_until('./kubectl get pods','todo.*Running',note='Get the pod name of our new pod.')
		podname = shutit.send_and_get_output("""./kubectl get pods | grep todo | awk '{print $1}'""")
		shutit.send('kubectl expose pod ' + podname + ' --target-port=8000 --port=80')
		shutit.send('kubectl get service')
		shutit.get_url('skydns.yaml.in',['http://kubernetes.io/docs/getting-started-guides/docker-multinode'])
		shutit.get_url('kube-system.yaml',['http://kubernetes.io/docs/getting-started-guides/docker-multinode'])
		shutit.send('export DNS_REPLICAS=1')
		shutit.send('export DNS_DOMAIN=cluster.local # specify in startup parameter `--cluster-domain` for containerized kubelet ')
		shutit.send('export DNS_SERVER_IP=10.0.0.10  # specify in startup parameter `--cluster-dns` for containerized kubelet ')
		shutit.send('''sed -e "s/{{ pillar\['dns_replicas'\] }}/${DNS_REPLICAS}/g;s/{{ pillar\['dns_domain'\] }}/${DNS_DOMAIN}/g;s/{{ pillar\['dns_server'\] }}/${DNS_SERVER_IP}/g" skydns.yaml.in > ./skydns.yaml''')
		shutit.send('kubectl create -f ./kube-system.yaml')
		shutit.send('kubectl create -f ./skydns.yaml')
		shutit.logout()
		shutit.logout()
		return True

	def get_config(self, shutit):
		# CONFIGURATION
		# shutit.get_config(module_id,option,default=None,boolean=False)
		#                                    - Get configuration value, boolean indicates whether the item is
		#                                      a boolean type, eg get the config with:
		# shutit.get_config(self.module_id, 'myconfig', default='a value')
		#                                      and reference in your code with:
		# shutit.cfg[self.module_id]['myconfig']
		shutit.get_config(self.module_id,'vagrant_image',default='ubuntu/trusty64')
		shutit.get_config(self.module_id,'vagrant_provider',default='virtualbox')
		shutit.get_config(self.module_id,'kubernetes_version',default='1.2.0')
		return True

def module():
	return shutit_kubernetes(
		'tk.shutit.shutit_kubernetes', 1845506479.0001125135135,
		description='',
		maintainer='',
		delivery_methods=['bash'],
		depends=['shutit.tk.setup','shutit-library.virtualbox.virtualbox.virtualbox','tk.shutit.vagrant.vagrant.vagrant']
	)
