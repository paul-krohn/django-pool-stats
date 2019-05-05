# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "ubuntu/bionic65"

  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
    v.cpus = 2
  end

  config.vm.network "forwarded_port", guest: 8000, host: 8000
  config.vm.network "forwarded_port", guest: 3306, host: 13306

  if ENV.has_key?('DJANGO_CHEF_ROOT')
    config.vm.synced_folder "#{ENV['DJANGO_CHEF_ROOT']}", "/chef"
    config.vm.provision "shell", inline: "/bin/bash /vagrant/provision.sh"
  end

end
