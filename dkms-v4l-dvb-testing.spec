
%define name	dkms-%dkmsname
%define dkmsname v4l-dvb-testing
%define oname	v4l-dvb
%define version 0
%define snapshot 14014
%define rel	2

# Set the minimum kernel version that should be supported.
# Setting a lower version automatically drops modules that depend
# on a newer kernel.
%define minkernel 2.6.32
%if %{mdkversion} <= 201000
%define minkernel 2.6.31
%endif
%if %{mdkversion} <= 200910
%define minkernel 2.6.29
%endif
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
URL:		https://linuxtv.org/
# rm -rf v4l-dvb; hg clone http://linuxtv.org/hg/v4l-dvb
# cd v4l-dvb; hg archive -ttbz2 ../v4l-dvb-$(hg tip --template {rev}).tar.bz2; cd ..
Source:		%oname-%snapshot.tar.bz2
# fixes build on mnb patched 2.6.31 kernels
Source1:	v4l-dvb-2.6.31mnb.patch
# Disable DVB_DUMMY_FE
Patch1:		v4l-dvb-disable-dvb-dummy-fe.patch
BuildRoot:	%{_tmppath}/%{name}-root
Patch2:		v4l-dvb-add-sq930x-support.patch
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
%patch1 -p1
%patch2 -p1 -b .sq930x~

%build
cd v4l
%make allyesconfig Makefile.media Makefile.sound .myconfig VER=%minkernel SRCDIR=$(rpm -ql $(rpm -q --requires %kernelpkg | grep ^kernel-) | grep '\.config' | sed 's,/.config,,')

%if %{mdkversion} <= 200910
# no necessary headers in kernel-devel
echo 'CONFIG_DVB_FIREDTV_IEEE1394 := n' >> .myconfig
%endif

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

mkdir -p %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/patches
install -m644 %{SOURCE1} %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/patches/

cat > %{buildroot}%{_usrsrc}/%{dkmsname}-%{version}-%{release}/dkms.conf <<EOF
PACKAGE_NAME="%{dkmsname}"
PACKAGE_VERSION="%{version}-%{release}"
PATCH[0]="v4l-dvb-2.6.31mnb.patch"
PATCH_MATCH[0]="2\.6\.31\.[1-9].*mnb"
MAKE[0]="make -j \\\$(/usr/bin/getconf _NPROCESSORS_ONLN) -Cv4l all SRCDIR=\$kernel_source_dir"
CLEAN="make -Cv4l clean || :"
AUTOINSTALL=yes
EOF

i=0
for module in $(cat v4l/modulelist | xargs -n1 | sort -u); do
	if [ "$module" = "v4l2-compat-ioctl32" ]; then
		# hacked here to avoid more Makefile.* parsing logic above
		grep "^CONFIG_COMPAT=y" $(rpm -ql $(rpm -q --requires %kernelpkg | grep ^kernel-) | grep '\.config') || continue
	fi
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


%changelog
* Sun Dec 05 2010 Oden Eriksson <oeriksson@mandriva.com> 0-0.hg14014.2mdv2011.0
+ Revision: 610255
- rebuild

  + Per Øyvind Karlsen <peroyvind@mandriva.org>
    - add support for sq930x (P2)

* Sat Jan 23 2010 Anssi Hannula <anssi@mandriva.org> 0-0.hg14014.1mdv2010.1
+ Revision: 495163
- new snapshot
- rediff disable-dvb-dummy-fe.patch
- build for 2.6.32 on 2010.1+
- add 2.6.31mnb support patch to make the new snapshot build on 2.6.31
  with mandriva patches
- use parallel build on multi-core systems as the build takes quite a
  long time

* Sat Aug 08 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg12407.1mdv2010.0
+ Revision: 411757
- new snapshot
- drop workaround-if-endif-bug.patch, now unneeded
- fix dkms build failure on 2009.1

* Sat Mar 14 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10837.4mdv2009.1
+ Revision: 355165
- replace previous hack by dropping incorrect Kconfig if/endif block
  handling from make_kconfig.pl (workaround-if-endif-bug.patch)
- disable DVB_DUMMY_FE (disable-dvb-dummy-fe.patch)

* Sun Mar 08 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10837.3mdv2009.1
+ Revision: 352866
- workaround bug in make_kconfig.pl by re-enabling DVB_FE_CUSTOMISE for now

* Sun Mar 08 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10837.2mdv2009.1
+ Revision: 352813
- actually disable v4l2-compat-ioctl32 on 32bit

* Sat Mar 07 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10837.1mdv2009.1
+ Revision: 351746
- new snapshot

* Sat Mar 07 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10785.2mdv2009.1
+ Revision: 351598
- disable noarch, 64bit has more modules (compat stuff), fixes dkms build
  on 32bit

* Tue Mar 03 2009 Anssi Hannula <anssi@mandriva.org> 0-0.hg10785.1mdv2009.1
+ Revision: 347864
- new snapshot
- build for 2.6.29 on cooker

* Fri Dec 05 2008 Anssi Hannula <anssi@mandriva.org> 0-0.hg9767.1mdv2009.1
+ Revision: 310779
- new snapshot
- provide another stub script

* Sat Nov 01 2008 Anssi Hannula <anssi@mandriva.org> 0-0.hg9500.1mdv2009.1
+ Revision: 299164
- add executable bit to all stub scripts
- new snapshot (fixes 2.6.27 support)
- fix random file time race condition build errors by including more
  stub scripts
- remove wrong comment

* Tue May 20 2008 Anssi Hannula <anssi@mandriva.org> 0-0.hg7901.1mdv2009.0
+ Revision: 209519
- new snapshot

* Sun May 04 2008 Anssi Hannula <anssi@mandriva.org> 0-0.hg7826.1mdv2009.0
+ Revision: 201126
- initial Mandriva release

