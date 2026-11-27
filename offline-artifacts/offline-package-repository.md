# Offline OS Package Repository

## Yum Repository Creation

Create a local Yum repository from offline RPM packages:

```bash
# Install repo tools
sudo yum install yum-utils

# Create repository directory
sudo mkdir -p /opt/local/repo/yum
sudo chown -R root:root /opt/local/repo/yum

# Copy RPM packages to the repository directory
sudo cp *.rpm /opt/local/repo/yum/

# Generate the repository metadata
sudo createrepo_c /opt/local/repo/yum

# Verify repository
sudo repoquery --content /opt/local/repo/yum | head -20
```

### Yum Repository with GPG Signing

```bash
# Generate GPG key pair (if not already exists)
gpg --full-generate-key

# Export the public key
gpg --export > /etc/pki/rpm-gpg/RPM-GPG-KEY-local

# Export the private key for signing
gpg --export-secret-keys > /etc/pki/rpm-gpg/RPM-GPG-KEY-local-priv

# Import the key into Yum keyring
sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-local

# Create signed repository
sudo createrepo_c -- underlay_dir /opt/local/repo/yum --policy signed \
  --gpgkey /etc/pki/rpm-gpg/RPM-GPG-KEY-local --repoclosure

# Update Yum client configuration to trust the repository
cat <<'EOF' | sudo tee /etc/yum.repos.d/local.repo
[local-repo]
name=Local Offline Yum Repository
basefile:///opt/local/repo/yum
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-local
EOF
```

## Debian Repository Creation

Create a local Debian repository from offline .deb packages:

```bash
# Install repo tools
sudo apt-get install dpkg-dev

# Create repository directory
sudo mkdir -p /opt/local/repo/debian
sudo chown -R root:root /opt/local/repo/debian

# Copy .deb packages to the repository directory
sudo cp *.deb /opt/local/repo/debian/

# Generate Packages.gz file
sudo dpkg-scanpackages /opt/local/repo/debian /dev/null | gzip > /opt/local/repo/debian/Packages.gz

# Generate Release file (metadata signature)
sudoapt-ftparchive release /opt/local/repo/debian > /opt/local/repo/debian/Release

# Optional: add component and label information
cat <<'EOF' | sudo tee /opt/local/repo/debian/Release
Origin: Local Offline Debian Repository
Label: local-repo
Suite: stable
Codename: $(lsb_release -c -a)
Version: 1.0
Architectures: amd64 i386 arm64
EOF
```

### Debian Repository with GPG Signing

```bash
# Generate GPG key for signing
gpg --full-generate-key

# Export the public key
gpg --export > /usr/share/keyrings/local-repo.gpg

# Export the private key for signing
gpg --export-secret-keys > /usr/share/keyrings/local-repo-priv.gpg

# Create signed repository
sudo dpkg-scanpackages /opt/local/repo/debian /dev/null | \
  gpg --clearsign --default-key <key-id> \
  --output /opt/local/repo/debian/Release.gpg

# Generate Release file with signature
gpg --yes --default-key <key-id> --sign --publish-domain local \
  --output /opt/local/repo/debian/Release \
  /opt/local/repo/debian/Release.gpg

# Update apt configuration to trust the repository
cat <<'EOF' | sudo tee /etc/apt/sources.list.d/local.list
deb [signed-by=/usr/share/keyrings/local-repo.gpg] file:/opt/local/repo/debian stable main
EOF

# Update package lists
sudo apt-get update
```

## Repository Synchronization

### Yum Synchronization

```bash
# Mirror repository to another location
sudo reposync --repoid=local-repo --newest-only --download_path /opt/backup/yum/

# or use createmirror
sudo createmirror /etc/yum.repos.d/local.repo /opt/backup/yum/

# Synchronize with remote repository (if network available)
sudo rsync -avz /opt/local/repo/yum/ user@remote-host:/opt/remote/repo/yum/
```

### Debian Synchronization

```bash
# Mirror repository structure
sudo rsync -avz /opt/local/repo/debian/ user@remote-host:/opt/remote/repo/debian/

# or use apt-mirror
sudo apt-mirror /etc/apt/mirror.conf

# Synchronize package lists
sudo rsync -avz /opt/local/repo/debian/Release* user@remote-host:/opt/remote/repo/debian/
```

## Client Configuration

### Yum Client Configuration

```bash
# Enable the local repository
sudo yum-config-manager --add-repo file:///etc/yum.repos.d/local.repo

# Disable all other repositories and use only local
sudo yum-config-manager --disable '*'
sudo yum-config-manager --enable local-repo

# List available packages from local repository
yum list available --disabled='*' --enabled=local-repo

# Install package from local repository
sudo yum install package-name
```

### Debian Client Configuration

```bash
# Enable the local repository
sudo apt-get update

# Pin the local repository priority
cat <<'EOF' | sudo tee /etc/apt/preferences.d/local-pin
Package: *
Pin: release o=Local Offline Debian Repository
Pin-Priority: 900
EOF

# Install package from local repository
sudo apt-get install package-name
```

## Package Dependency Resolution in Air-Gapped Environments

### Yum Dependency Resolution

```bash
# Install package with all dependencies from local repository
sudo yum localinstall /opt/local/repo/yum/package-name.rpm

# Solve dependencies without installing
sudo yum deplist package-name --disablerepo='*' --enablerepo=local-repo

# Resolve and download missing dependencies
sudo yum-builddep -y /opt/local/repo/yum/package-name.spec

# Manual dependency resolution
# 1. List package dependencies
rpm -qpR /opt/local/repo/yum/package-name.rpm

# 2. Install missing dependencies recursively
sudo yum localinstall --disablerepo='*' --enablerepo=local-repo \
  $(rpm -qpR /opt/local/repo/yum/package-name.rpm | tr '\n' ' ')
```

### Debian Dependency Resolution

```bash
# Install package with dependencies from local repository
sudo apt-get install ./package-name.deb

# Resolve build dependencies
sudo apt-get build-dep package-name

# Check unresolved dependencies
dpkg -s package-name | grep -E "^(Depends|Status):"

# Manual dependency resolution with dpkg
# 1. Download all dependencies first
apt-get --download-only install package-name

# 2. Install downloaded debs in correct order
sudo dpkg -i /var/cache/apt/archives/*.deb

# 2. Fix any remaining issues
sudo apt-get -f install
```

### Air-Gapped Dependency Extraction

```bash
# Extract dependencies from offline media
# Yum: repo-create with --downloadonly option
sudo yum install --downloadonly --disablerepo='*' --enablerepo=local-repo \
  -d /opt/downloads package-name

# Debian: apt-get with --print-uris to list all debs
apt-get --print-uris install package-name | grep "'" | cut -d"'" -f2 | \
  xargs -I{} wget -P /opt/downloads {}

# Create consolidated repository from downloaded packages
# Yum
sudo createrepo_c /opt/downloads/yum

# Debian
sudo dpkg-scanpackages /opt/downloads/debian /dev/null | gzip > /opt/downloads/debian/Packages.gz
```

### Dependency Conflict Resolution

```bash
# Yum: show what would be installed and why
sudo yum check-update --disablerepo='*' --enablerepo=local-repo
sudo yum depsolve --disablerepo='*' --enablerepo=local-repo \
  package-name

# Debian: show dependency conflicts
apt-cache show package-name | grep -E "^(Depends|Version):"
sudo dpkg -C  # check for broken state

# Force install with --force-depends (use with caution)
sudo yum localinstall --force --nodeps /opt/local/repo/yum/package-name.rpm
sudo dpkg --force-depends -i /opt/local/repo/debian/package-name.deb
```

### Verifying Installed Package Dependencies

```bash
# Yum
rpm -q --requires package-name
rpm -q --whatprovides $(rpm -q --requires package-name | grep 'library-name' | cut -d' ' -f1)

# Debian
dpkg -l package-name
apt-cache depends package-name
```