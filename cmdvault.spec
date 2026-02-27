# CmdVault RPM spec file for Fedora Linux
# Build: rpmbuild -ta cmdvault-1.0.tar.gz (tarball contains cmdvault-1.0/ with this spec and cmdvault/)

Name:       cmdvault
Version:    1.0
Release:    1%{?dist}
Summary:    Personal command knowledge base for terminal commands
License:    MIT
URL:        https://github.com/cmdvault/cmdvault
Source0:    %{name}-%{version}.tar.gz
BuildArch:  noarch

Requires:   python3 >= 3.9
Requires:   python3-tkinter

%description
CmdVault is a desktop application that stores terminal commands under
categories, supports fuzzy search, and allows one-click or one-key
copying to clipboard. Think of it as a local, searchable CLI cheat-sheet.

%prep
%autosetup -n %{name}-%{version}

%build
# No compilation; pure Python

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/cmdvault

install -d %{buildroot}%{_datadir}/cmdvault
install -m 644 cmdvault/*.py %{buildroot}%{_datadir}/cmdvault/

cat > %{buildroot}%{_bindir}/cmdvault << EOF
#!/bin/bash
export PYTHONPATH="%{_datadir}:\$PYTHONPATH"
exec python3 -m cmdvault.main "\$@"
EOF
chmod 755 %{buildroot}%{_bindir}/cmdvault

install -m 644 packaging/cmdvault.desktop %{buildroot}%{_datadir}/applications/

%files
%{_bindir}/cmdvault
%{_datadir}/cmdvault/
%{_datadir}/applications/cmdvault.desktop

%changelog
* Fri Feb 28 2026 - 1.0-1
- Initial package
