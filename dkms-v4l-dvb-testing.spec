
%define name	dkms-%dkmsname
%define dkmsname v4l-dvb-testing
%define oname	v4l-dvb
%define version 0
%define snapshot 10785
%define rel	2

# Set the minimum kernel version that should be supported.
# Setting a lower version automatically drops modules that depend
# on a newer kernel.
%define minkernel 2.6.29
%if %{mdkversion} <= 200900
%define minkernel 2.6.27
%endif
%if %{mdkversion} <= 200810
%define minkernel 2.6.24
%endif
# Set the minimum kernel package that should be supported.
# The package may fail to build against a kernel that has disabled
# features compared to this reference kernel.
%define kernelpkg kernel-desktop-devel-latest

%define release %mkrel 0.hg%snapshot.%rel

Summary:	Experimental version of Linux V4L/DVB subsystem
Name:		%{name}
Version:	%{version}
Release:	%{release}
Group:		System/Kernel and hardware
License:	GPLv2
URL:		http://linuxtv.org/
# rm -rf v4l-dvb; hg clone http://linuxtv.org/hg/v4l-dvb
# cd v4l-dvb; hg archive -ttbz2 ../v4l-dvb-$(hg tip --template {rev}).tar.bz2; cd ..
Source:		%oname-%snapshot.tar.bz2
BuildRoot:	%{_tmppath}/%{name}-root
# 64bit has v4l2-compat-ioctl32.ko, 32bit does not, thus not noarch
#BuildArch:	noarch
Requires:	dkms
Requires(post):	dkms
Requires(preun): dkms
# Used to build the config:
BuildRequires:	%kernelpkg >= %minkernel

%description
DKMS module package for the v4l-dvb hg development tree from
linuxtv.org. Use this package to test a new snapshot of the V4L/DVB
subsystem of the Linux kernel.

%prep
%setup -q -n %oname-%snapshot
cd v4l
%make allyesconfig Makefile.media Makefile.sound .myconfig VER=%minkernel SRCDIR=$(rpm -ql $(rpm -q --requires %kernelpkg | grep ^kernel-) | grep '\.config' | sed 's,/.config,,')

%install
rm -rf %{buildroot}
install -d -m755 %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}
cp -a v4l linux %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}
rm -f %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/v4l/scripts/*
install -m755 v4l/scripts/make_config_compat.pl %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/v4l/scripts/
for script in rmmod.pl make_makefile.pl make_myconfig.pl make_kconfig.pl; do
	echo "#!/bin/true" > %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/v4l/scripts/$script
	chmod 0755 %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/v4l/scripts/$script
done

cd v4l
rm -f modulelist
cat Makefile.media Makefile.sound | while read input; do
	[[ "$input" =~ ^obj-\$ ]] || continue
	if [[ "$input" =~ CONFIG_ ]]; then
		grep -q $(echo "$input" | sed -r -ne 's/^obj-\$\((CONFIG.*)\).*$/\1/p')= .config || continue
	fi
	echo "$input" | cut -d= -f2 | sed 's,\.o,,g' >> modulelist
done
cd -

cat > %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/dkms.conf <<EOF
PACKAGE_NAME="%{dkmsname}"
PACKAGE_VERSION="%{version}-%{release}"
MAKE[0]="make -Cv4l all SRCDIR=\$kernel_source_dir"
CLEAN="make -Cv4l clean"
AUTOINSTALL=yes
EOF

i=0
for module in $(cat v4l/modulelist | xargs -n1 | sort -u); do
	cat >> %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/dkms.conf <<-EOF
	BUILT_MODULE_NAME[$i]="$module"
	BUILT_MODULE_LOCATION[$i]="v4l"
	DEST_MODULE_LOCATION[$i]="/kernel/%dkmsname"
	EOF
	i=$((i+1))
done

%post
dkms add     -m %{dkmsname} -v %{version}-%{release} --rpm_safe_upgrade &&
dkms build   -m %{dkmsname} -v %{version}-%{release} --rpm_safe_upgrade &&
dkms install -m %{dkmsname} -v %{version}-%{release} --rpm_safe_upgrade --force
true

%preun
dkms remove  -m %{dkmsname} -v %{version}-%{release} --rpm_safe_upgrade --all
true

%files
%defattr(-,root,root)
%{_usrsrc}/%{dkmsname}-%{version}-%{release}
