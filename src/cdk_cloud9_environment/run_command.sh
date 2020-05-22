if [ $(readlink -f /dev/xvda) = "/dev/xvda" ]
then
  # Rewrite the partition table so that the partition takes up all the space that it can.
  sudo growpart /dev/xvda 1
  # Expand the size of the file system.
  sudo resize2fs /dev/xvda1
else
  # Rewrite the partition table so that the partition takes up all the space that it can.
  sudo growpart /dev/nvme0n1 1
  # Expand the size of the file system.
  sudo resize2fs /dev/nvme0n1p1
fi
cd /
VERSION=3.7.4
yum update -y
yum install awscli gcc git gzip openssl rsync unzip which zip openssl-devel bzip2-devel libffi-devel -y && yum clean all && rm -rf /var/cache/yum
curl -sL https://rpm.nodesource.com/setup_10.x | bash - 
yum -y install nodejs && yum clean all && rm -rf /var/cache/yum && npm set unsafe-perm true
echo "installing Yarn"
curl -sSL https://dl.yarnpkg.com/rpm/yarn.repo | tee /etc/yum.repos.d/yarn.repo
yum -y install yarn && yum clean all && rm -rf /var/cache/yum

wget --quiet https://www.python.org/ftp/python/${VERSION}/Python-${VERSION}.tgz
tar xzf Python-${VERSION}.tgz
cd Python-${VERSION}
echo "Building Python"
./configure --enable-optimizations
echo "Installing Python"
make altinstall
cd /
# Remove old symlinks
rm -rf /etc/alternatives/pip
rm -rf /etc/alternatives/python
# make new symlinks
ln -s /usr/local/bin/pip${VERSION:0:3} /etc/alternatives/pip
ln -s /usr/local/bin/python${VERSION:0:3} /etc/alternatives/python
ln -s /usr/local/bin/pip-3.7 /usr/bin/pip3

## Java
wget --quiet https://corretto.aws/downloads/latest/amazon-corretto-8-x64-linux-jdk.rpm
yum localinstall amazon-corretto*.rpm -y
## Install Maven
wget --quiet https://www-us.apache.org/dist/maven/maven-3/3.6.3/binaries/apache-maven-3.6.3-bin.tar.gz -P /tmp
tar xf /tmp/apache-maven-3.6.3-bin.tar.gz -C /opt
ln -s /opt/apache-maven-3.6.3 /opt/maven
## User Local stuff (brew HATES to be run by root)
cd /home/ec2-user/
echo "Creating user-script"
cat <<'EOF' > ./script.sh
## DoteNet
sh -c "$(curl -fsSL https://dot.net/v1/dotnet-install.sh)"
## AWS SAM
CI=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
test -d ~/.linuxbrew && eval $(~/.linuxbrew/bin/brew shellenv)
test -d /home/linuxbrew/.linuxbrew && eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)
test -r ~/.bash_profile && echo "eval \$($(brew --prefix)/bin/brew shellenv)" >>~/.bash_profile
echo "eval \$($(/home/linuxbrew/.linuxbrew/bin/brew --prefix)/bin/brew shellenv)" >>~/.profile
npm uninstall -g aws-sam-local
sudo pip uninstall aws-sam-cli
sudo rm -rf $(which sam)
brew tap aws/tap
brew install aws-sam-cli
ln -sf $(which sam) ~/.c9/bin/sam

##
npm uninstall -g typescript
npm install -g typescript
tsc --version
# Set up Maven Environment Variables
echo 'export JAVA_HOME=/usr/lib/jvm/java-1.8.0-amazon-corretto' >> /home/ec2-user/.bashrc
echo 'export M2_HOME=/opt/maven' >> /home/ec2-user/.bashrc
echo 'export MAVEN_HOME=/opt/maven' >> /home/ec2-user/.bashrc
echo 'export PATH=${M2_HOME}/bin:${PATH}' >> /home/ec2-user/.bashrc
echo 'export PATH=$PATH:/home/ec2-user/.dotnet' >> /home/ec2-user/.bashrc
echo 'export CHARSET=UTF-8' >> /home/ec2-user/.bashrc
echo 'export LC_ALL=C.UTF-8' >> /home/ec2-user/.bashrc

cd ~/
EOF
echo "Running user-script"
chmod +x ./script.sh
runuser -l  ec2-user -c './script.sh'