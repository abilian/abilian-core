# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
#  config.vm.box = "hashicorp/bionic64"

#  config.vm.provider :virtualbox do |vb|
#    vb.memory = 1024
#    vb.cpus = 2
#  end

  config.vm.provider "docker" do |d|
    d.image = "ubuntu/bionic"
  end

  config.vm.provision :shell, path: "etc/provision.sh"
end
