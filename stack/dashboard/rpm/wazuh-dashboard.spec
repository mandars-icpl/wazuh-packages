# Wazuh dashboard SPEC
# Copyright (C) 2021, Wazuh Inc.
#
# This program is a free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public
# License (version 2) as published by the FSF - Free Software
# Foundation.
Summary:     Wazuh dashboard is a user interface and visualization tool for security-related data. Documentation can be found at https://documentation.wazuh.com/current/getting-started/components/wazuh-dashboard.html
Name:        wazuh-dashboard
Version:     %{_version}
Release:     %{_release}
License:     GPL
Group:       System Environment/Daemons
Source0:     %{name}-%{version}.tar.gz
URL:         https://www.wazuh.com/
buildroot:   %{_tmppath}/%{name}-%{version}-%{release}-wazuh-dashboard-%(%{__id_u} -n)
Vendor:      Wazuh, Inc <info@wazuh.com>
Packager:    Wazuh, Inc <info@wazuh.com>
Requires(pre):    /usr/sbin/groupadd /usr/sbin/useradd
Requires(preun):  /sbin/service
Requires(postun): /sbin/service
AutoReqProv: no
Requires: libcap
ExclusiveOS: linux

# -----------------------------------------------------------------------------

%global USER %{name}
%global GROUP %{name}
%global CONFIG_DIR /etc/%{name}
%global PID_DIR /run/%{name}
%global INSTALL_DIR /usr/share/%{name}
%global DASHBOARD_FILE wazuh-dashboard-base-%{version}-%{release}-linux-x64.tar.xz
%define _source_payload w9.gzdio
%define _binary_payload w9.gzdio

# -----------------------------------------------------------------------------


%description
Wazuh dashboard is a user interface and visualization tool for security-related data. This Wazuh central component enables exploring, visualizing, and analyzing the stored security alerts generated by the Wazuh server. Wazuh dashboard enables inspecting the status and managing the configurations of the Wazuh cluster and agents as well as creating and managing users and roles. In addition, it allows testing the ruleset and making calls to the Wazuh API. Documentation can be found at https://documentation.wazuh.com/current/getting-started/components/wazuh-dashboard.html

# -----------------------------------------------------------------------------

%prep

cp /tmp/%{DASHBOARD_FILE} ./

groupadd %{GROUP}
useradd -g %{GROUP} %{USER}

# -----------------------------------------------------------------------------

%build

tar -xf %{DASHBOARD_FILE}

# Set custom config dir
sed -i 's/OSD_NODE_OPTS_PREFIX/OSD_PATH_CONF="\/etc\/wazuh-dashboard" OSD_NODE_OPTS_PREFIX/g' "wazuh-dashboard-base/bin/opensearch-dashboards"
sed -i 's/OSD_USE_NODE_JS_FILE_PATH/OSD_PATH_CONF="\/etc\/wazuh-dashboard" OSD_USE_NODE_JS_FILE_PATH/g' "wazuh-dashboard-base/bin/opensearch-dashboards-keystore"

# -----------------------------------------------------------------------------

%install

mkdir -p %{buildroot}%{CONFIG_DIR}
mkdir -p %{buildroot}%{INSTALL_DIR}
mkdir -p %{buildroot}/etc/systemd/system
mkdir -p %{buildroot}%{_initrddir}
mkdir -p %{buildroot}/etc/default

cp wazuh-dashboard-base/etc/node.options %{buildroot}%{CONFIG_DIR}
cp wazuh-dashboard-base/etc/opensearch_dashboards.yml %{buildroot}%{CONFIG_DIR}
cp wazuh-dashboard-base/VERSION %{buildroot}%{INSTALL_DIR}

mv wazuh-dashboard-base/* %{buildroot}%{INSTALL_DIR}

# Set custom welcome styles

mkdir -p %{buildroot}%{INSTALL_DIR}/config

cp %{buildroot}%{INSTALL_DIR}/etc/services/wazuh-dashboard.service %{buildroot}/etc/systemd/system/wazuh-dashboard.service
cp %{buildroot}%{INSTALL_DIR}/etc/services/default %{buildroot}/etc/default/wazuh-dashboard

chmod 640 %{buildroot}/etc/systemd/system/wazuh-dashboard.service
chmod 640 %{buildroot}/etc/default/wazuh-dashboard

rm -rf %{buildroot}%{INSTALL_DIR}/etc/

find %{buildroot}%{INSTALL_DIR} -exec chown %{USER}:%{GROUP} {} \;
find %{buildroot}%{CONFIG_DIR} -exec chown %{USER}:%{GROUP} {} \;

chown root:root %{buildroot}/etc/systemd/system/wazuh-dashboard.service

if [ "%{version}" = "99.99.0" ];then
    runuser %{USER} --shell="/bin/bash" --command="%{buildroot}%{INSTALL_DIR}/bin/opensearch-dashboards-plugin install https://packages-dev.wazuh.com/futures/ui/dashboard/wazuh-99.99.0-%{release}.zip"
else
    runuser %{USER} --shell="/bin/bash" --command="%{buildroot}%{INSTALL_DIR}/bin/opensearch-dashboards-plugin install %{_url}"
fi

find %{buildroot}%{INSTALL_DIR}/plugins/wazuh/ -exec chown %{USER}:%{GROUP} {} \;
find %{buildroot}%{INSTALL_DIR}/plugins/wazuh/ -type f -perm 644 -exec chmod 640 {} \;
find %{buildroot}%{INSTALL_DIR}/plugins/wazuh/ -type f -perm 755 -exec chmod 750 {} \;
find %{buildroot}%{INSTALL_DIR}/plugins/wazuh/ -type d -exec chmod 750 {} \;
find %{buildroot}%{INSTALL_DIR}/plugins/wazuh/ -type f -perm 744 -exec chmod 740 {} \;

# -----------------------------------------------------------------------------

%pre
# Create the wazuh-dashboard group if it doesn't exists
if [ $1 = 1 ]; then
  if command -v getent > /dev/null 2>&1 && ! getent group %{GROUP} > /dev/null 2>&1; then
    groupadd -r %{GROUP}
  elif ! getent group %{GROUP} > /dev/null 2>&1; then
    groupadd -r %{GROUP}
  fi
  # Create the wazuh-dashboard user if it doesn't exists
  if ! getent passwd %{USER} > /dev/null 2>&1; then
    useradd -g %{GROUP} -G %{USER} -d %{INSTALL_DIR}/ -r -s /sbin/nologin wazuh-dashboard
  fi
fi
# Stop the services to upgrade the package
if [ $1 = 2 ]; then
  if command -v systemctl > /dev/null 2>&1 && systemctl > /dev/null 2>&1 && systemctl is-active --quiet wazuh-dashboard > /dev/null 2>&1; then
    systemctl stop wazuh-dashboard.service > /dev/null 2>&1
    touch %{INSTALL_DIR}/wazuh-dashboard.restart
  # Check for SysV
  elif command -v service > /dev/null 2>&1 && service wazuh-dashboard status 2>/dev/null | grep "is running" > /dev/null 2>&1; then
    service wazuh-dashboard stop > /dev/null 2>&1
    touch %{INSTALL_DIR}/wazuh-dashboard.restart
  fi
fi

# -----------------------------------------------------------------------------

%post
setcap 'cap_net_bind_service=+ep' %{INSTALL_DIR}/node/bin/node

# -----------------------------------------------------------------------------

%preun
if [ $1 = 0 ];then # Remove
  echo -n "Stopping wazuh-dashboard service..."
  if command -v systemctl > /dev/null 2>&1 && systemctl > /dev/null 2>&1; then
      systemctl stop wazuh-dashboard.service > /dev/null 2>&1
  # Check for SysV
  elif command -v service > /dev/null 2>&1; then
    service wazuh-dashboard stop > /dev/null 2>&1
  fi
fi

# -----------------------------------------------------------------------------

%postun
if [ $1 = 0 ];then
  # If the package is been uninstalled
  # Remove the wazuh-dashboard user if it exists
  if getent passwd %{USER} > /dev/null 2>&1; then
    userdel %{USER} >/dev/null 2>&1
  fi
  # Remove the wazuh-dashboard group if it exists
  if command -v getent > /dev/null 2>&1 && getent group %{GROUP} > /dev/null 2>&1; then
    groupdel %{GROUP} >/dev/null 2>&1
  elif getent group %{GROUP} > /dev/null 2>&1; then
    groupdel %{GROUP} >/dev/null 2>&1
  fi

  # Remove /etc/wazuh-dashboard and /usr/share/wazuh-dashboard dirs
  rm -rf %{INSTALL_DIR}
  if [ -d %{PID_DIR} ]; then
    rm -rf %{PID_DIR}
  fi
fi

# -----------------------------------------------------------------------------

# posttrans code is the last thing executed in a install/upgrade
%posttrans
if [ ! -d %{PID_DIR} ]; then
    mkdir -p %{PID_DIR}
    chown %{USER}:%{GROUP} %{PID_DIR}
fi

# Move keystore file if upgrade (file exists in install dir in <= 4.6.0)
if [ -f "%{INSTALL_DIR}"/config/opensearch_dashboards.keystore ]; then
  mv "%{INSTALL_DIR}"/config/opensearch_dashboards.keystore "%{CONFIG_DIR}"/opensearch_dashboards.keystore
elif [ ! -f %{CONFIG_DIR}/opensearch_dashboards.keystore ]; then
  runuser %{USER} --shell="/bin/bash" --command="%{INSTALL_DIR}/bin/opensearch-dashboards-keystore create" > /dev/null 2>&1
  runuser %{USER} --shell="/bin/bash" --command="echo kibanaserver | %{INSTALL_DIR}/bin/opensearch-dashboards-keystore add opensearch.username --stdin" > /dev/null 2>&1
  runuser %{USER} --shell="/bin/bash" --command="echo kibanaserver | %{INSTALL_DIR}/bin/opensearch-dashboards-keystore add opensearch.password --stdin" > /dev/null 2>&1
  chmod 640 "%{CONFIG_DIR}"/opensearch_dashboards.keystore
fi

if [ -f %{INSTALL_DIR}/wazuh-dashboard.restart ]; then
  rm -f %{INSTALL_DIR}/wazuh-dashboard.restart
  if command -v systemctl > /dev/null 2>&1 && systemctl > /dev/null 2>&1; then
    systemctl restart wazuh-dashboard.service > /dev/null 2>&1
  # Check for SysV
  elif command -v service > /dev/null 2>&1; then
    service wazuh-dashboard restart > /dev/null 2>&1
  fi

fi


# -----------------------------------------------------------------------------

%clean
rm -fr %{buildroot}

# -----------------------------------------------------------------------------

%files
%defattr(-,%{USER},%{GROUP})
%dir %attr(750, %{USER}, %{GROUP}) %{CONFIG_DIR}

%attr(0750, %{USER}, %{GROUP}) "/etc/default/wazuh-dashboard"
%config(noreplace) %attr(0640, %{USER}, %{GROUP}) "%{CONFIG_DIR}/opensearch_dashboards.yml"
%attr(440, %{USER}, %{GROUP}) %{INSTALL_DIR}/VERSION
%dir %attr(750, %{USER}, %{GROUP}) %{INSTALL_DIR}
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/core"
%attr(-, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/core/*"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/remove"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/list"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/lib"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/downloaders"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/utils"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/root"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/harden"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/__fixtures__"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/__fixtures__/plugin"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/__fixtures__/plugin/foo"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/plugins"
%attr(-, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/plugins/*
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__/reload_logging_config"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/rotate"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/core"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/localization"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/warnings"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/http"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/keystore"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/bootstrap"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/apm"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/docs"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node_modules"
%attr(-, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node_modules/*"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node_modules/.yarn-integrity"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node"
%attr(-, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node/*"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/node/bin/node"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/data"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/plugins"
%attr(-, %{USER}, %{GROUP}) "%{INSTALL_DIR}/plugins/*"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/bin"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/remove/settings.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/remove/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/remove/remove.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/dev.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/list/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/list/list.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/lib/logger.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/lib/errors.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/lib/log_warnings.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/opensearch_dashboards.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/downloaders/file.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/downloaders/http.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/zip.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/download.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/install.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/settings.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/rename.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/invalid_name.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/test_plugin_different_version.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/banana.jpg"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/test_plugin_no_opensearch_dashboards.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/test_plugin.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/corrupt.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/__fixtures__/replies/test_plugin_many.zip"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/cleanup.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/pack.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/install/progress.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/cli.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_plugin/dist.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/cli_keystore.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/add.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/create.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/utils/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/utils/prompt.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/dev.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/get_keystore.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/remove.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/dist.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli_keystore/list.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/apm.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/root/force.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/root/is_root.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/root/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/polyfill.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/node_version_validator.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/harden/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/harden/child_process.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/harden/lodash_template.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/no_transpilation.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/exit_on_warning.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/setup_node_env/dist.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/np_ui_plugin_public_dirs.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/optimize_mixin.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/proxy_bundles_route.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/file_hash.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/file_hash_cache.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/__fixtures__/plugin/foo/plugin.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/__fixtures__/outside_output.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/bundles_route.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/optimize/bundles_route/dynamic_asset_response.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/command.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/help.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/cli.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/serve.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/read_keystore.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__/invalid_config.yml"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__/reload_logging_config/opensearch_dashboards_log_file.test.yml"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__/reload_logging_config/opensearch_dashboards_log_console.test.yml"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/serve/integration_tests/__fixtures__/reload_logging_config/opensearch_dashboards.test.yml"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/cli/dist.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils/unset.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils/version.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils/artifact_type.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/utils/deep_clone_with_buffers.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/rotate/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/rotate/log_rotator.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/apply_filters_to_keys.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_format.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_reporter.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_format_json.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_with_metadata.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/configuration.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_interceptor.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/logging/log_format_string.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/core/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/localization/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/localization/telemetry_localization_collector.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/localization/file_integrity.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/get_translations_path.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/i18n/constants.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/osd_server.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/warnings/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/http/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/http/register_hapi_plugins.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/http/setup_base_path_provider.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config/override.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config/complete.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config/schema.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/config/config.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/keystore/keystore.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/keystore/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/server/keystore/errors.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_mixin.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/ui_render_mixin.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/bootstrap/osd_bundles_loader_source.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/bootstrap/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/bootstrap/template.js.hbs"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/ui_render/bootstrap/app_bootstrap.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/legacy/ui/apm/index.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/docs/docs_repo.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/src/docs/cli.js"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/package.json"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/manifest.yml"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/LICENSE.txt"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/NOTICE.txt"
%attr(640, %{USER}, %{GROUP}) "%{INSTALL_DIR}/README.txt"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/bin/use_node"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/bin/opensearch-dashboards"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/bin/opensearch-dashboards-plugin"
%attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/bin/opensearch-dashboards-keystore"
%dir %attr(750, %{USER}, %{GROUP}) "%{INSTALL_DIR}/config"
%attr(640, %{USER}, %{GROUP}) "%{CONFIG_DIR}/node.options"
%attr(640, root, root) "/etc/systemd/system/wazuh-dashboard.service"

%changelog
* Fri Dec 15 2023 support <info@wazuh.com> - 4.8.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-8-0.html
* Tue Nov 07 2023 support <info@wazuh.com> - 4.7.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-7-0.html
* Mon Oct 16 2023 support <info@wazuh.com> - 4.6.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-6-0.html
* Wed Sep 06 2023 support <info@wazuh.com> - 4.5.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-3.html
* Thu Aug 31 2023 support <info@wazuh.com> - 4.5.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-2.html
* Thu Aug 24 2023 support <info@wazuh.com> - 4.5.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5.1.html
* Thu Aug 10 2023 support <info@wazuh.com> - 4.5.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-5-0.html
* Mon Jul 10 2023 support <info@wazuh.com> - 4.4.5
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-5.html
* Tue Jun 13 2023 support <info@wazuh.com> - 4.4.4
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-4.html
* Thu May 25 2023 support <info@wazuh.com> - 4.4.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-3.html
* Mon Apr 24 2023 support <info@wazuh.com> - 4.4.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-2.html
* Mon Apr 17 2023 support <info@wazuh.com> - 4.4.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-1.html
* Wed Jan 18 2023 support <info@wazuh.com> - 4.4.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-4-0.html
* Thu Nov 10 2022 support <info@wazuh.com> - 4.3.10
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-10.html
* Mon Oct 03 2022 support <info@wazuh.com> - 4.3.9
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-9.html
* Mon Sep 19 2022 support <info@wazuh.com> - 4.3.8
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-8.html
* Mon Aug 08 2022 support <info@wazuh.com> - 4.3.7
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-7.html
* Thu Jul 07 2022 support <info@wazuh.com> - 4.3.6
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-6.html
* Wed Jun 29 2022 support <info@wazuh.com> - 4.3.5
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-5.html
* Tue Jun 07 2022 support <info@wazuh.com> - 4.3.4
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-4.html
* Tue May 31 2022 support <info@wazuh.com> - 4.3.3
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-3.html
* Mon May 30 2022 support <info@wazuh.com> - 4.3.2
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-2.html
* Wed May 18 2022 support <info@wazuh.com> - 4.3.1
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-1.html
* Thu May 05 2022 support <info@wazuh.com> - 4.3.0
- More info: https://documentation.wazuh.com/current/release-notes/release-4-3-0.html
